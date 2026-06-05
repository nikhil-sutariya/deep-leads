"""
Lead Discovery Agent - Finds qualified leads using AI providers (Gemini or Perplexity)
"""
import json
import re
import httpx
from typing import List, Dict, Optional
from google import genai
from google.genai import types
from loguru import logger
from google.genai.errors import APIError

from app.core.config import get_settings
from app.schemas.lead import (
    BuiltDiscoveryPrompt,
    ExtractionResult,
    CompanyInfo,
    Lead,
    LeadStatus,
)
from app.prompts.lead_discovery_prompts import build_extraction_prompt


class LeadDiscoveryAgent:
    """AI Agent for discovering qualified business leads"""
    
    def __init__(self):
        self.settings = get_settings()
        self.provider = self.settings.ai_provider.lower()
        
        # Initialize based on provider
        if self.provider == "gemini":
            self.client = genai.Client(api_key=self.settings.google_api_key)
            self.grounding_tool = types.Tool(google_search=types.GoogleSearch())
        elif self.provider == "perplexity":
            if not self.settings.perplexity_api_key:
                raise ValueError("Perplexity API key not configured")
            self.perplexity_api_key = self.settings.perplexity_api_key
        else:
            raise ValueError(f"Unsupported AI provider: {self.provider}")
        
    def discover_from_prompt(
        self,
        built_prompt: BuiltDiscoveryPrompt,
        max_results: int = 50,
    ) -> List[Lead]:
        """
        Main entry point: discover leads from a prompt produced by the
        `PromptBuilderAgent`.

        Args:
            built_prompt: Output of the prompt builder agent.
            max_results: Maximum number of leads to return.

        Returns:
            List of discovered leads, scored and sorted by quality.
        """
        logger.info(f"Starting lead discovery — intent: {built_prompt.intent_summary}")

        leads = self._run_search(built_prompt.discovery_prompt)

        validated_leads = self._validate_leads(leads)
        final_leads = validated_leads[:max_results]

        logger.info(f"Discovery complete: Found {len(final_leads)} qualified leads")
        return final_leads

    def _run_search(self, discovery_prompt: str) -> List[Lead]:
        """Run the AI search using a pre-built prompt and parse results into leads."""
        try:
            response = self._call_ai_provider(discovery_prompt)
            if not response['success']:
                logger.info(response['reason'])
                return []

            extraction_prompt = build_extraction_prompt(response['results'])
            formatted_response = self._call_extraction_prompt(extraction_prompt)

            leads = self._parse_extraction_response(formatted_response)

            logger.info(f"Found {len(leads)} companies from discovery prompt")
            return leads

        except Exception as e:
            logger.error(f"Error running discovery search: {e}")
            return []
    
    def _call_ai_provider(self, prompt: str) -> str:
        """Route to the configured AI provider"""
        if self.provider == "gemini":
            return self._call_gemini(prompt)
        elif self.provider == "perplexity":
            return self._call_perplexity(prompt)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
        
    def _call_extraction_prompt(self, prompt: str) -> dict:
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=prompt,
            )
            
            text = response.text.strip()

            # Remove code fences if Gemini still adds them
            if text.startswith("```"):
                text = text.strip("`")
                # typical: ```json\n ... \n```
                if "json" in text.split("\n")[0]:
                    text = "\n".join(text.split("\n")[1:])
                if text.endswith("```"):
                    text = text[:-3]

            return json.loads(text)

        except Exception as e:
            raise RuntimeError(f"Extraction prompt failed: {e}")
    
    def _call_gemini(self, prompt: str) -> Dict: # Changed return type hint for clarity
        """
        Calls Gemini API with Google Search grounding, managing the multi-turn
        conversation required for grounding and retrieving the final text.
        """
        
        contents = [prompt]
        
        config = types.GenerateContentConfig(
            tools=[self.grounding_tool]
        )
        
        # 2. Start the main loop (Limit to 3 turns)
        for i in range(3): 
            try:
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash-lite", 
                    contents=contents,
                    config=config
                )
            except APIError as e:
                # CORRECTED: Return a dictionary for the caller
                return {"success": False, "results": None, "reason": f"Gemini API error occurred: {e}"}

            # 3. Check for the final text response
            if response.text:
                # THIS IS THE SUCCESSFUL OUTCOME
                return {"success": True, "results": response.text, "reason": None}
                
            # 4. Check for a Google Search Tool Call
            if response.function_calls:
                # Append the model's call part to the contents history.
                contents.append(response.candidates[0].content)
                continue # Go to the next loop iteration (which executes the search)
                
            # 5. Handle unexpected scenarios (Safety, Blocked)
            else:
                if not response.candidates:
                    return {"success": False, "results": None, "reason": "Response was empty and contained no candidates."}
                
                candidate = response.candidates[0]
                
                if candidate.finish_reason == types.FinishReason.SAFETY:
                    # Corrected: Ensure response key exists even if None
                    return {"success": False, "results": response.text, "reason": "The response was blocked due to safety concerns."}
                
                # Fallback for other issues
                return {"success": False, "results": response.text, "reason": "Response is missing text and function calls for an unknown reason."}
                
        # CORRECTED: Loop exhausted failure return
        return {"success": False, "results": None, "reason": "Failed to get a text response after multiple tool-calling turns (3 loops)."
    }
    
    def _call_perplexity(self, prompt: str) -> str:
        """Call Perplexity API with online search"""
        
        url = "https://api.perplexity.ai/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.perplexity_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "sonar",  # Perplexity's online model
            "messages": [
                {
                    "role": "system",
                    "content": "You are a lead discovery assistant that finds qualified business leads based on specific criteria. Provide accurate, real-time information from online sources."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 2048
        }
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                
                result = response.json()
                return result['choices'][0]['message']['content']
                
        except httpx.HTTPError as e:
            logger.error(f"Perplexity API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error calling Perplexity: {e}")
            raise
    
    def _normalize_company(self, raw: dict) -> dict:
        cleaned = {}

        # --- 1) Clean name ---
        cleaned["name"] = raw.get("name")

        # --- 2) Clean website ---
        website = raw.get("website")
        if website:
            website = website.strip().lower().replace(" ", "")
            
            # add protocol if missing
            if not website.startswith(("http://", "https://")):
                website = "https://" + website
            
            # remove trailing slash
            if website.endswith("/"):
                website = website[:-1]

        cleaned["website"] = website

        # --- 3) Clean employee_count ---
        emp = raw.get("employee_count")
        if isinstance(emp, str):
            # "4-9"
            match = re.match(r"(\d+)", emp)
            if match:
                emp = int(match.group(1))
            else:
                # "Less than 100"
                match = re.findall(r"\d+", emp)
                emp = int(match[0]) if match else None

        cleaned["employee_count"] = emp

        # --- 4) Clean funding_stage ---
        stage = raw.get("funding_stage", "")
        if isinstance(stage, str):
            stage = stage.strip().replace(" ", "")
            stage = stage.replace("Round", "")
            stage = stage.replace("Pre-seed", "Pre-Seed")
            stage = stage.replace("PreSeed", "Pre-Seed")
            stage = stage.replace("Pre-Seed/Seed", "Seed")
            stage = stage.replace("SeedRound", "Seed")
            stage = stage.title()

            VALID = ["Pre-Seed", "Seed", "SeriesA", "SeriesB", "SeriesC+", "Bootstrapped", "Public"]
            mapped = None
            for v in VALID:
                if stage.lower().startswith(v.lower().replace("+", "")):
                    mapped = v
                    break
            cleaned["funding_stage"] = mapped or "Unknown"

        # --- 5) Funding amount rename ---
        amt = raw.get("funding_amount") or raw.get("funding_amount_millions")
        # Handle dict case (extract numeric value if present)
        if isinstance(amt, dict):
            amt = amt.get("value") or amt.get("amount") or None
        if isinstance(amt, str):
            nums = re.findall(r"\d+", amt)
            amt = float(nums[0]) if nums else None
        # Ensure amt is a number before comparison
        if amt is not None and isinstance(amt, (int, float)) and amt > 1000:  # if user gives actual dollars e.g., 8,000,000
            amt = round(amt / 1_000_000, 2)
        cleaned["funding_amount_millions"] = amt if isinstance(amt, (int, float)) else None

        # --- 6) Rename description ---
        cleaned["description"] = raw.get("description")

        # --- 7) Location & contact mapping ---
        cleaned["location"] = raw.get("location")
        cleaned["city"] = raw.get("city")
        cleaned["country"] = raw.get("country")

        # Pass through contact details if the discovery step found them
        phone = raw.get("phone")
        if isinstance(phone, str):
            phone = phone.strip() or None
        cleaned["phone"] = phone

        email = raw.get("email")
        if isinstance(email, str):
            from app.utils.email_sanitize import extract_first_email
            email = extract_first_email(email.strip()) or None
        cleaned["email"] = email

        address = raw.get("address")
        if isinstance(address, str):
            address = address.strip() or None
        cleaned["address"] = address

        # optional: extract city/country from location later if needed

        # --- 8) Tech stack cleaning ---
        tech = raw.get("tech_stack") or raw.get("tech_focus")
        if isinstance(tech, str):
            cleaned["tech_stack"] = [t.strip() for t in tech.split(",")]
        elif isinstance(tech, list):
            cleaned["tech_stack"] = tech

        # --- 9) Industry cleaning ---
        cleaned["industry"] = raw.get("industry")

        return cleaned
    
    def _parse_extraction_response(self, raw_json: dict) -> List[Lead]:
        try:
            # If raw_json is a JSON string → load it
            if isinstance(raw_json, str):
                raw_json = json.loads(raw_json)

            # If list → wrap
            if isinstance(raw_json, list):
                raw_json = {"companies": raw_json}

            companies_raw = raw_json.get("companies", [])

            normalized = [self._normalize_company(c) for c in companies_raw]

            # Now safe to validate
            extracted = ExtractionResult(companies=normalized)

            leads = []
            for company in extracted.companies:
                leads.append(
                    Lead(
                        company_info=company,
                        status=LeadStatus.DISCOVERED
                    )
                )

            return leads

        except Exception as e:
            raise RuntimeError(f"Failed parsing extraction response: {e}")


   
    def _validate_leads(self, leads: List[Lead]) -> List[Lead]:
        """Drop obviously-bad records.

        With the prompt-driven flow we no longer enforce hard min/max filters
        here — the discovery prompt itself encodes the user's targeting.
        We only drop records that lack a company name.
        """
        validated = []

        for lead in leads:
            try:
                if not lead.company_info.name:
                    continue
                validated.append(lead)
            except Exception as e:
                logger.warning(f"Error validating lead {lead.company_info.name}: {e}")
                continue

        return validated

