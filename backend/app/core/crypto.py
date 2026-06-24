"""
Symmetric encryption for stored secrets (e.g. per-user SMTP passwords).

Uses Fernet (AES-128-CBC + HMAC) with a key derived from `settings.secret_key`,
so no extra configuration is required. If `secret_key` changes, previously
encrypted values can no longer be decrypted (they must be re-entered).
"""
import base64
import hashlib
from functools import lru_cache
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from loguru import logger

from app.core.config import get_settings


@lru_cache()
def _fernet() -> Fernet:
    settings = get_settings()
    digest = hashlib.sha256(settings.secret_key.encode()).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a plaintext secret into a urlsafe token string."""
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(token: Optional[str]) -> Optional[str]:
    """Decrypt a token back to plaintext; returns None if missing/invalid."""
    if not token:
        return None
    try:
        return _fernet().decrypt(token.encode()).decode()
    except (InvalidToken, Exception) as e:  # noqa: BLE001 - never raise from decrypt
        logger.warning(f"Failed to decrypt secret: {e}")
        return None
