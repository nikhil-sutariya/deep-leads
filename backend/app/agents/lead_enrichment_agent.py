"""
Lead Enrichment Agent.

Aligned with the new business-type-agnostic discovery flow, this agent's job is to
**fill in missing contact details** so a salesperson can reach out. It is NOT a
tech-centric intelligence-gathering agent anymore.

Primary outputs (all gap-filled — never clobber values already on the lead):
- Company website (filled on `company_info.website` if discovery missed it)
- Company contact: `company_info.phone`, `company_info.email`, `company_info.address`
- Decision makers: name, title, email, linkedin_url, phone
- Social media: LinkedIn, Twitter, Facebook, Instagram, YouTube, GitHub
"""
import asyncio
import json
from typing import Any, Dict, List, Optional

import httpx
from google import genai
from google.genai import types
from google.genai.errors import APIError
from loguru import logger

from app.core.config import get_settings
from app.schemas.lead import ContactInfo, Lead, LeadEnrichmentData, LeadStatus
from app.prompts.enrichment_prompts import (
    build_company_contact_extraction_prompt,
    build_decision_maker_extraction_prompt,
    get_company_contact_prompt,
    get_decision_maker_prompt,
)


class LeadEnrichmentAgent:
    """AI Agent for filling in missing CONTACT details on a lead."""

    def __init__(self):
        self.settings = get_settings()
        self.provider = self.settings.ai_provider.lower()

        if self.provider == "gemini":
            self.client = genai.Client(api_key=self.settings.google_api_key)
            self.grounding_tool = types.Tool(google_search=types.GoogleSearch())
        elif self.provider == "perplexity":
            if not self.settings.perplexity_api_key:
                raise ValueError("Perplexity API key not configured")
            self.perplexity_api_key = self.settings.perplexity_api_key
        else:
            raise ValueError(f"Unsupported AI provider: {self.provider}")

    # --------------------------- Public entry points -------------------------- #

    async def enrich_lead(self, lead: Lead) -> Lead:
        """Enrich a lead by finding the most important contact details:
        website, company phone / email / address, decision makers, social media.

        Gracefully gap-fills — only writes values that are currently missing on
        the lead, so we never clobber data the discovery agent already produced.
        """
        logger.info(f"Enriching lead: {lead.company_info.name}")

        try:
            lead.status = LeadStatus.ENRICHING

            existing = lead.enrichment_data or LeadEnrichmentData()

            # 1. Company-level contact info (website / phone / email / address / social)
            contact = await self._find_company_contact(lead)

            if contact.get("website") and not lead.company_info.website:
                lead.company_info.website = contact["website"]
            if contact.get("phone") and not lead.company_info.phone:
                lead.company_info.phone = contact["phone"]
            if contact.get("email") and not lead.company_info.email:
                lead.company_info.email = contact["email"]
            if contact.get("address") and not lead.company_info.address:
                lead.company_info.address = contact["address"]

            merged_social = dict(existing.social_media or {})
            merged_social.update(
                {k: v for k, v in (contact.get("social_media") or {}).items() if v}
            )
            social_media = merged_social or None

            # 2. Decision makers — always refresh (emails and roles change)
            decision_makers = await self._find_decision_makers(lead)

            # 3. Compose updated enrichment data
            enrichment_data = LeadEnrichmentData(
                decision_makers=decision_makers or existing.decision_makers,
                social_media=social_media,
                additional_data=existing.additional_data,
            )

            lead.enrichment_data = enrichment_data
            lead.status = LeadStatus.ENRICHED

            logger.info(f"Successfully enriched: {lead.company_info.name}")
            return lead

        except Exception as e:
            logger.error(f"Error enriching lead {lead.company_info.name}: {e}")
            lead.status = LeadStatus.DISCOVERED
            raise

    async def batch_enrich_leads(self, leads: List[Lead], max_concurrent: int = 3) -> List[Lead]:
        """Enrich multiple leads with bounded concurrency to respect rate limits."""

        enriched_leads: List[Lead] = []

        for i in range(0, len(leads), max_concurrent):
            batch = leads[i : i + max_concurrent]

            tasks = [self.enrich_lead(lead) for lead in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Enrichment failed: {result}")
                else:
                    enriched_leads.append(result)

            await asyncio.sleep(2)

        return enriched_leads

    # ----------------------------- Per-step calls ----------------------------- #

    async def _find_company_contact(self, lead: Lead) -> Dict[str, Any]:
        """Find company-level website / phone / email / address / social media."""

        prompt = get_company_contact_prompt(
            company_name=lead.company_info.name,
            website=str(lead.company_info.website) if lead.company_info.website else "unknown",
            location=(
                lead.company_info.location
                or lead.company_info.city
                or lead.company_info.country
                or "unknown"
            ),
            industry=lead.company_info.industry or "unknown",
        )

        try:
            response = await self._call_ai_provider_async(prompt)
            if not response["success"]:
                logger.info(response["reason"])
                return {}

            extraction_prompt = build_company_contact_extraction_prompt(response["results"])
            structured = await self._call_extraction_prompt_async(extraction_prompt)
            return self._parse_contact_response(structured)

        except Exception as e:
            logger.error(f"Error finding company contact for {lead.company_info.name}: {e}")
            return {}

    async def _find_decision_makers(self, lead: Lead) -> List[ContactInfo]:
        """Find decision makers appropriate for this business type."""

        prompt = get_decision_maker_prompt(
            company_name=lead.company_info.name,
            website=str(lead.company_info.website) if lead.company_info.website else "unknown",
            industry=lead.company_info.industry,
        )

        try:
            response = await self._call_ai_provider_async(prompt)
            if not response["success"]:
                logger.info(response["reason"])
                return []

            extraction_prompt = build_decision_maker_extraction_prompt(response["results"])
            structured = await self._call_extraction_prompt_async(extraction_prompt)

            decision_makers = self._parse_decision_makers(structured)
            logger.info(
                f"Found {len(decision_makers)} decision makers for {lead.company_info.name}"
            )
            return decision_makers

        except Exception as e:
            logger.error(f"Error finding decision makers for {lead.company_info.name}: {e}")
            return []

    # ---------------------------- AI provider calls --------------------------- #

    async def _call_ai_provider_async(self, prompt: str) -> Dict[str, Any]:
        """Route to the configured AI provider (async)."""

        if self.provider == "gemini":
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, self._call_gemini, prompt)
        if self.provider == "perplexity":
            results = await self._call_perplexity_async(prompt)
            return {"success": True, "results": results, "reason": None}
        raise ValueError(f"Unsupported provider: {self.provider}")

    def _call_gemini(self, prompt: str) -> Dict[str, Any]:
        """Call Gemini with Google Search grounding, looping through tool calls."""

        contents: List[Any] = [prompt]
        config = types.GenerateContentConfig(tools=[self.grounding_tool])

        for _ in range(3):
            try:
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash-lite",
                    contents=contents,
                    config=config,
                )
            except APIError as e:
                return {"success": False, "results": None, "reason": f"Gemini API error: {e}"}

            if response.text:
                return {"success": True, "results": response.text, "reason": None}

            if response.function_calls:
                contents.append(response.candidates[0].content)
                continue

            if not response.candidates:
                return {"success": False, "results": None, "reason": "Empty response from Gemini."}

            candidate = response.candidates[0]
            if candidate.finish_reason == types.FinishReason.SAFETY:
                return {"success": False, "results": response.text, "reason": "Response blocked for safety."}

            return {"success": False, "results": response.text, "reason": "No text and no tool call."}

        return {"success": False, "results": None, "reason": "Failed after 3 tool-call turns."}

    async def _call_perplexity_async(self, prompt: str) -> str:
        """Call Perplexity's online model."""

        url = "https://api.perplexity.ai/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.perplexity_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "sonar",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a research assistant that finds public contact details "
                        "for businesses (any type of business — not just tech). Use only "
                        "publicly verifiable information."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 2048,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
        except httpx.HTTPError as e:
            logger.error(f"Perplexity API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error calling Perplexity: {e}")
            raise

    def _call_extraction_prompt(self, prompt: str) -> Dict[str, Any]:
        """Run a structured-JSON extraction pass through Gemini Flash-Lite."""

        try:
            if not hasattr(self, "client"):
                raise RuntimeError("Extraction prompts require the Gemini client to be configured.")
            response = self.client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=prompt,
            )
            text = (response.text or "").strip()

            if text.startswith("```"):
                text = text.strip("`")
                first_line, _, rest = text.partition("\n")
                if first_line.strip().lower().startswith("json"):
                    text = rest
                if text.endswith("```"):
                    text = text[:-3]

            return json.loads(text)
        except Exception as e:
            raise RuntimeError(f"Extraction prompt failed: {e}")

    async def _call_extraction_prompt_async(self, prompt: str) -> Dict[str, Any]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._call_extraction_prompt, prompt)

    # ----------------------------- Response parsers --------------------------- #

    def _parse_contact_response(self, payload: Any) -> Dict[str, Any]:
        """Convert the extracted company-contact JSON into a clean dict."""

        if isinstance(payload, str):
            payload = json.loads(payload)
        if not isinstance(payload, dict):
            return {}

        contact = {
            "website": self._sanitize_text(payload.get("website")),
            "phone": self._sanitize_text(payload.get("phone")),
            "email": self._sanitize_email(payload.get("email")),
            "address": self._sanitize_text(payload.get("address")),
            "social_media": self._sanitize_dict(payload.get("social_media")),
        }
        return {k: v for k, v in contact.items() if v}

    def _parse_decision_makers(self, payload: Any) -> List[ContactInfo]:
        """Convert the extracted decision-maker JSON into ContactInfo records."""

        if isinstance(payload, str):
            payload = json.loads(payload)

        contacts_raw: List[Dict[str, Any]] = []
        if isinstance(payload, dict):
            contacts_raw = payload.get("decision_makers") or payload.get("contacts") or []
        elif isinstance(payload, list):
            contacts_raw = payload

        decision_makers: List[ContactInfo] = []
        for entry in contacts_raw:
            if not isinstance(entry, dict):
                continue

            contact_data = {
                "name": entry.get("name"),
                "title": entry.get("title"),
                "email": self._sanitize_email(entry.get("email")),
                "linkedin_url": entry.get("linkedin_url"),
                "phone": entry.get("phone"),
            }

            try:
                decision_makers.append(ContactInfo(**contact_data))
            except Exception as exc:
                logger.debug(f"Skipping invalid contact record: {exc}")
                continue

        return decision_makers[:5]

    # ------------------------------- Sanitizers ------------------------------- #

    @staticmethod
    def _sanitize_text(value: Any) -> Optional[str]:
        # Note: bool is a subclass of int — exclude it so True/False never become "True"/"False".
        if isinstance(value, bool):
            return None
        if isinstance(value, (str, int, float)):
            text = str(value).strip()
            return text or None
        return None

    @staticmethod
    def _sanitize_email(value: Any) -> Optional[str]:
        from app.utils.email_sanitize import extract_first_email

        text = LeadEnrichmentAgent._sanitize_text(value)
        return extract_first_email(text) if text else None

    @staticmethod
    def _sanitize_dict(value: Any) -> Optional[Dict[str, str]]:
        """Keep only clean string values (e.g. social URLs).

        The model sometimes returns booleans like {"linkedin": true} to mean
        "has a profile"; those carry no usable value, so we drop them rather
        than letting them break Dict[str, str] validation downstream.
        """
        if not isinstance(value, dict):
            return None
        cleaned: Dict[str, str] = {}
        for k, v in value.items():
            text = LeadEnrichmentAgent._sanitize_text(v)
            if text and text.lower() not in ("true", "false", "none", "null"):
                cleaned[str(k)] = text
        return cleaned or None
