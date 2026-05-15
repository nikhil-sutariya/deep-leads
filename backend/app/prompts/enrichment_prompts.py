"""
Prompts for the lead enrichment agent.

The enrichment agent's job is to **fill in missing contact details** so a
salesperson can reach out — website, company phone, company email, address,
social media, and decision makers. It is intentionally NOT focused on
tech-centric signals (pain points, technology needs, growth signals,
competitor analysis), because the new lead discovery flow is business-type
agnostic — leads may be restaurants, manufacturers, retailers, agencies,
non-profits, etc., where those signals are not meaningful.
"""
from typing import Optional


# ----------------------------- Company contact ----------------------------- #


def get_company_contact_prompt(
    company_name: str,
    website: str,
    location: str,
    industry: str,
) -> str:
    """Prompt the agent to find company-level contact details."""

    return f"""You are a research assistant. Find the most up-to-date public CONTACT
details for the company below so a salesperson can reach out.

COMPANY: {company_name}
KNOWN WEBSITE: {website}
KNOWN LOCATION: {location}
INDUSTRY / TYPE: {industry}

FIND (any that are publicly available):
1. The company's primary website URL (especially important if the KNOWN WEBSITE above is "unknown" or looks wrong).
2. A general contact phone number for the company (HQ / main line).
3. A general contact email (info@, contact@, hello@, sales@ — whichever is publicly listed).
4. The company's primary office or mailing address.
5. Official social media profile URLs — LinkedIn (company page), Twitter / X, Facebook,
   Instagram, YouTube, GitHub. Only include the ones that actually exist for this company.

RULES:
- Only return information that is publicly verifiable.
- If a piece of information cannot be found, omit it or leave it null — do NOT guess
  or fabricate phone numbers, emails, or URLs.
- Prefer official sources (the company's own website, official LinkedIn page) over
  third-party listings.
- Skip any tech-stack analysis, pain points, news, or competitor research — those
  are not relevant to this task.

A separate extractor will turn your findings into structured JSON, so feel free to
list the details in plain text with clear labels.
"""


def build_company_contact_extraction_prompt(contact_response: str) -> str:
    """Convert the company-contact research into strict JSON."""

    return f"""Convert the following company contact research into a strict JSON object.

SOURCE TEXT:
\"\"\"
{contact_response}
\"\"\"

OUTPUT RULES:
- Return ONLY a JSON object, no prose, no markdown fences.
- Use null for unknown values.
- Keys must match exactly. Do NOT add extra keys.

TARGET STRUCTURE:
{{
  "website": null,
  "phone": null,
  "email": null,
  "address": null,
  "social_media": {{
    "linkedin": null,
    "twitter": null,
    "facebook": null,
    "instagram": null,
    "youtube": null,
    "github": null
  }}
}}
"""


# ----------------------------- Decision makers ----------------------------- #


def get_decision_maker_prompt(
    company_name: str,
    website: str,
    industry: Optional[str] = None,
) -> str:
    """Prompt the agent to find the right decision makers for THIS type of business."""

    industry_hint = f" (industry / type: {industry})" if industry else ""

    return f"""Find the most senior decision makers at {company_name} ({website}){industry_hint}
who would be the right point of contact for B2B outreach.

The roles you target MUST match the type of business — pick what's appropriate. Examples:
- Startup / scale-up      → Founder, CEO, CTO, VP Engineering / Operations, Head of Product
- Small / family business → Owner, Managing Director, General Manager, Partner
- Restaurant / hospitality→ Owner, GM, Director of Operations, Beverage Director
- Manufacturer / industrial → Plant Manager, Director of Operations, VP Engineering, Procurement Head
- Retail / e-commerce     → Founder, Head of E-commerce, Head of Buying, Marketing Director
- Agency / consultancy    → Founder, Managing Partner, Head of Growth, Practice Lead
- Healthcare / clinic     → Owner, Medical Director, Chief Administrator, Practice Manager
- Non-profit              → Executive Director, Board Chair, Director of Programs
- Public / large company  → C-suite, EVPs, SVPs, divisional VPs relevant to the buyer use case

FIND FOR EACH PERSON:
- Full name
- Exact current job title
- LinkedIn profile URL
- Most likely email (only if the company's email pattern is known — e.g., firstname.lastname@…)
- Direct phone number, if publicly available
- A 1-line note on why they are relevant (recent hire, owner, key influencer, etc.)

RULES:
- Only return information that is publicly verifiable.
- Do NOT fabricate email addresses you can't reasonably derive from a known pattern.
  If uncertain, leave the email as null.
- Prefer CURRENT decision makers (not departed employees).
- Return 3–5 most relevant contacts, ranked by likelihood to respond.
"""


def build_decision_maker_extraction_prompt(decision_maker_response: str) -> str:
    return f"""Extract decision makers from the following text and return ONLY a JSON object
with a "decision_makers" array.

SOURCE:
\"\"\"
{decision_maker_response}
\"\"\"

Each decision maker must follow this structure:
{{
  "name": null,
  "title": null,
  "email": null,
  "linkedin_url": null,
  "phone": null,
  "background": null
}}

RULES:
- Return ONLY the JSON object. No prose, no markdown fences.
- If a field is missing, set it to null.
- Limit to the 5 most relevant contacts.
"""
