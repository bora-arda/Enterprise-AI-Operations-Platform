"""Password hashing and JWT helpers."""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

import jwt

from procurement_ai.config.settings import get_settings

PBKDF2_ITERATIONS = 260_000
PBKDF2_ALGORITHM = "sha256"


def hash_password(password: str) -> str:
    """Hash a password with PBKDF2-SHA256 and a random salt."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        PBKDF2_ALGORITHM,
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    return f"pbkdf2_{PBKDF2_ALGORITHM}${PBKDF2_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, encoded: str | None) -> bool:
    """Verify a password against a stored PBKDF2 hash (constant time)."""
    if not encoded:
        return False
    try:
        scheme, iterations_raw, salt, expected = encoded.split("$", 3)
        if scheme != f"pbkdf2_{PBKDF2_ALGORITHM}":
            return False
        iterations = int(iterations_raw)
    except (ValueError, AttributeError):
        return False

    digest = hashlib.pbkdf2_hmac(
        PBKDF2_ALGORITHM,
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    return hmac.compare_digest(digest.hex(), expected)


def create_access_token(
    *,
    user_id: str,
    email: str,
    name: str,
    role: str,
) -> str:
    """Create a signed JWT access token."""
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "email": email,
        "name": name,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        "iss": "procurement-ai",
    }
    return jwt.encode(payload, settings.api_secret_key, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    """Decode and verify a JWT. Raises jwt.PyJWTError on failure."""
    settings = get_settings()
    return jwt.decode(
        token,
        settings.api_secret_key,
        algorithms=["HS256"],
        issuer="procurement-ai",
    )
