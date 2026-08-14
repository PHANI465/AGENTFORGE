"""API key generation, hashing, and BYOK key encryption.

Keys are high-entropy random tokens (not user-chosen passwords), so a fast
SHA-256 digest is the standard, appropriate way to hash them for lookup —
unlike passwords, there's no offline brute-force risk worth paying bcrypt's
cost for.

BYOK (Bring Your Own Key) LLM provider keys are encrypted at rest using
Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256).  The master key
is read from the ENCRYPTION_MASTER_KEY env var — a 32-byte URL-safe
base64 value generated once via:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

import hashlib
import os
import secrets

from cryptography.fernet import Fernet, InvalidToken

API_KEY_PREFIX = "afk_"

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        master_key = os.getenv("ENCRYPTION_MASTER_KEY", "")
        if not master_key:
            raise RuntimeError(
                "ENCRYPTION_MASTER_KEY env var is not set — "
                "generate one with: python -c "
                '"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
            )
        _fernet = Fernet(master_key.encode("utf-8"))
    return _fernet


def generate_api_key() -> str:
    return f"{API_KEY_PREFIX}{secrets.token_urlsafe(32)}"


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def encrypt_key(plaintext: str) -> str:
    """Encrypt a BYOK LLM key for storage.  Returns a URL-safe base64 string."""
    if not plaintext:
        return ""
    return _get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_key(ciphertext: str) -> str:
    """Decrypt a stored BYOK LLM key.  Returns empty string for empty input."""
    if not ciphertext:
        return ""
    try:
        return _get_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return ""
