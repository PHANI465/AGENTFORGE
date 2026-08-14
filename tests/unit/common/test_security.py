"""Unit tests for API key generation, hashing, and BYOK encryption."""


import pytest
from agentforge_common.security import (
    API_KEY_PREFIX,
    decrypt_key,
    encrypt_key,
    generate_api_key,
    hash_api_key,
)
from cryptography.fernet import Fernet


class TestGenerateApiKey:
    def test_starts_with_prefix(self) -> None:
        assert generate_api_key().startswith(API_KEY_PREFIX)

    def test_unique(self) -> None:
        assert generate_api_key() != generate_api_key()

    def test_sufficient_length(self) -> None:
        key = generate_api_key()
        assert len(key) > 40


class TestHashApiKey:
    def test_deterministic(self) -> None:
        key = "test-key"
        assert hash_api_key(key) == hash_api_key(key)

    def test_hex_digest(self) -> None:
        digest = hash_api_key("test")
        assert len(digest) == 64
        assert all(c in "0123456789abcdef" for c in digest)


@pytest.fixture(autouse=True)
def _set_encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENCRYPTION_MASTER_KEY", Fernet.generate_key().decode())
    import agentforge_common.security as sec

    sec._fernet = None


class TestEncryptDecrypt:
    def test_roundtrip(self) -> None:
        plaintext = "sk-abc123secretkey"
        ciphertext = encrypt_key(plaintext)
        assert ciphertext != plaintext
        assert decrypt_key(ciphertext) == plaintext

    def test_empty_string_passthrough(self) -> None:
        assert encrypt_key("") == ""
        assert decrypt_key("") == ""

    def test_ciphertext_is_different_each_time(self) -> None:
        plaintext = "sk-same-key"
        c1 = encrypt_key(plaintext)
        c2 = encrypt_key(plaintext)
        assert c1 != c2
        assert decrypt_key(c1) == decrypt_key(c2) == plaintext

    def test_invalid_ciphertext_returns_empty(self) -> None:
        assert decrypt_key("not-valid-base64-fernet-token") == ""

    def test_wrong_master_key_returns_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        plaintext = "sk-secret"
        ciphertext = encrypt_key(plaintext)

        import agentforge_common.security as sec

        monkeypatch.setenv("ENCRYPTION_MASTER_KEY", Fernet.generate_key().decode())
        sec._fernet = None

        assert decrypt_key(ciphertext) == ""

    def test_missing_master_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import agentforge_common.security as sec

        monkeypatch.delenv("ENCRYPTION_MASTER_KEY", raising=False)
        sec._fernet = None

        with pytest.raises(RuntimeError, match="ENCRYPTION_MASTER_KEY"):
            encrypt_key("sk-test")
