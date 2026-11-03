"""Unit tests for password hashing and JWT tokens."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from procurement_ai.auth.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from procurement_ai.config.settings import get_settings


class TestPasswordHashing:
    def test_hash_and_verify(self):
        encoded = hash_password("correct horse battery staple")
        assert encoded.startswith("pbkdf2_sha256$")
        assert verify_password("correct horse battery staple", encoded)
        assert not verify_password("wrong password", encoded)

    def test_missing_or_malformed_hash(self):
        assert not verify_password("x", None)
        assert not verify_password("x", "")
        assert not verify_password("x", "not-a-hash")
        assert not verify_password("x", "md5$1$salt$hash")

    def test_unique_salts(self):
        a = hash_password("same password")
        b = hash_password("same password")
        assert a != b
        assert verify_password("same password", a)
        assert verify_password("same password", b)


class TestTokens:
    def test_create_and_decode(self):
        token = create_access_token(
            user_id="11111111-1111-1111-1111-111111111111",
            email="user@example.com",
            name="Test User",
            role="manager",
        )
        payload = decode_access_token(token)
        assert payload["sub"] == "11111111-1111-1111-1111-111111111111"
        assert payload["email"] == "user@example.com"
        assert payload["role"] == "manager"
        assert payload["iss"] == "procurement-ai"

    def test_invalid_token(self):
        with pytest.raises(jwt.PyJWTError):
            decode_access_token("not-a-token")

    def test_expired_token(self):
        settings = get_settings()
        now = datetime.now(UTC)
        expired = jwt.encode(
            {
                "sub": "11111111-1111-1111-1111-111111111111",
                "email": "user@example.com",
                "name": "Test",
                "role": "manager",
                "iat": now - timedelta(hours=2),
                "exp": now - timedelta(hours=1),
                "iss": "procurement-ai",
            },
            settings.api_secret_key,
            algorithm="HS256",
        )
        with pytest.raises(jwt.PyJWTError):
            decode_access_token(expired)
