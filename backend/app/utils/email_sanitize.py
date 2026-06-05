"""Sanitize messy email strings from AI discovery/enrichment."""
import re
from typing import Optional

_EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)


def extract_first_email(value: Optional[str]) -> Optional[str]:
    """Return the first plausible email from a raw string, or None."""
    if not value or not str(value).strip():
        return None

    text = str(value).strip()

    for match in _EMAIL_RE.finditer(text):
        email = match.group(0).lower()
        if "@" in email and not email.startswith("@"):
            return email

    return None
