"""
Prompt Builder Agent.

Reads a user's free-form description of the leads they want to find, understands
the intent, and produces a detailed, self-contained discovery prompt that the
`LeadDiscoveryAgent` will run against an AI search provider.
"""
import json
from typing import Any, Dict

from google import genai
from loguru import logger

from app.core.config import get_settings
from app.prompts.prompt_builder_prompts import get_prompt_builder_prompt
from app.schemas.lead import BuiltDiscoveryPrompt


class PromptBuilderAgent:
    """Agent that converts a free-form user request into a targeted discovery prompt."""

    def __init__(self):
        self.settings = get_settings()
        # Reasoning step — always use Gemini even if the search provider is Perplexity
        self.client = genai.Client(api_key=self.settings.google_api_key)

    def build_discovery_prompt(self, user_query: str, max_results: int = 50) -> BuiltDiscoveryPrompt:
        """Convert the user's free-form request into a structured `BuiltDiscoveryPrompt`."""

        logger.info("Building discovery prompt from user query")

        prompt = get_prompt_builder_prompt(user_query=user_query, max_results=max_results)

        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            payload = self._extract_json(response.text)

            intent_summary = (payload.get("intent_summary") or "").strip()
            discovery_prompt = (payload.get("discovery_prompt") or "").strip()

            if not discovery_prompt:
                raise ValueError("Prompt builder returned an empty discovery_prompt")

            logger.info(f"Prompt builder intent: {intent_summary}")

            return BuiltDiscoveryPrompt(
                intent_summary=intent_summary or "Discover leads matching the user's description",
                discovery_prompt=discovery_prompt,
            )

        except Exception as exc:
            logger.error(f"Prompt builder failed, using passthrough fallback: {exc}")
            return BuiltDiscoveryPrompt(
                intent_summary="Direct pass-through of the user's request",
                discovery_prompt=self._fallback_prompt(user_query, max_results),
            )

    @staticmethod
    def _extract_json(text: str) -> Dict[str, Any]:
        """Tolerantly parse JSON from the model response, stripping common fences."""
        text = (text or "").strip()
        if text.startswith("```"):
            text = text.strip("`")
            first_line, _, rest = text.partition("\n")
            if first_line.strip().lower().startswith("json"):
                text = rest
            if text.endswith("```"):
                text = text[:-3]
        return json.loads(text)

    @staticmethod
    def _fallback_prompt(user_query: str, max_results: int) -> str:
        """A safe, generic discovery prompt used when the builder fails."""
        return (
            f"Find up to {max_results} companies matching the following user request. "
            f"Return active, currently-operating businesses with discoverable contact information. "
            f"For each company, provide: name, website, short description, industry, "
            f"employee count (estimate), funding stage and amount (if applicable), "
            f"location (city, country), founded year, tech stack or capability focus, "
            f"and any recent news.\n\n"
            f"USER REQUEST:\n{user_query}"
        )
