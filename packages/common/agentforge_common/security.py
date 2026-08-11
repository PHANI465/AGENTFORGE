"""API key generation/hashing.

Keys are high-entropy random tokens (not user-chosen passwords), so a fast
SHA-256 digest is the standard, appropriate way to hash them for lookup —
unlike passwords, there's no offline brute-force risk worth paying bcrypt's
cost for.
"""

import hashlib
import secrets

API_KEY_PREFIX = "afk_"


def generate_api_key() -> str:
    return f"{API_KEY_PREFIX}{secrets.token_urlsafe(32)}"


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
