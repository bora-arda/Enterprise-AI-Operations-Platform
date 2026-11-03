"""Input guardrails for safety and security."""

import logging
import re

logger = logging.getLogger(__name__)

# Patterns that might indicate prompt injection
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+(all\s+)?prior\s+instructions",
    r"disregard\s+(all\s+)?previous\s+instructions",
    r"forget\s+(all\s+)?previous\s+instructions",
    r"you\s+are\s+now\s+",
    r"new\s+instructions?\s*:",
    r"system\s+prompt\s*:",
    r"override\s+(all\s+)?previous\s+instructions",
]

# PII patterns
PII_PATTERNS = [
    (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN_REDACTED]"),
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL_REDACTED]"),
    (r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "[CARD_REDACTED]"),
]

MAX_INPUT_LENGTH = 2000


class InputGuard:
    """Input validation and safety checks."""

    @staticmethod
    def check_length(text: str) -> tuple[bool, str | None]:
        """Check input length."""
        if len(text) > MAX_INPUT_LENGTH:
            return False, f"Input exceeds maximum length of {MAX_INPUT_LENGTH} characters"
        return True, None

    @staticmethod
    def check_injection(text: str) -> tuple[bool, str | None]:
        """Check for prompt injection attempts."""
        text_lower = text.lower()
        for pattern in INJECTION_PATTERNS:
            if re.search(pattern, text_lower):
                return False, "Potential prompt injection detected"
        return True, None

    @staticmethod
    def detect_pii(text: str) -> list[str]:
        """Detect potential PII in text."""
        found = []
        for pattern, _ in PII_PATTERNS:
            matches = re.findall(pattern, text)
            found.extend(matches)
        return found

    @staticmethod
    def redact_pii(text: str) -> str:
        """Redact PII from text."""
        for pattern, replacement in PII_PATTERNS:
            text = re.sub(pattern, replacement, text)
        return text

    @classmethod
    def validate(cls, text: str) -> dict:
        """Run all input checks."""
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "pii_detected": [],
        }

        # Length check
        ok, error = cls.check_length(text)
        if not ok:
            result["valid"] = False
            result["errors"].append(error)

        # Injection check
        ok, error = cls.check_injection(text)
        if not ok:
            result["valid"] = False
            result["errors"].append(error)

        # PII detection
        pii = cls.detect_pii(text)
        if pii:
            result["warnings"].append(f"Potential PII detected: {len(pii)} instances")
            result["pii_detected"] = pii

        return result
