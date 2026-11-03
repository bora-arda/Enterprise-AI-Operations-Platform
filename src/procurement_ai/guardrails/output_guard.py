"""Output guardrails for response quality and safety."""

import logging
import re

logger = logging.getLogger(__name__)

# Patterns that might indicate hallucination
HALLUCINATION_PATTERNS = [
    r"as an ai(?:\s+language\s+model)?[,]?",
    r"i cannot\s+(?:access|retrieve|find)",
    r"i don't have\s+(?:access|information|data)",
    r"based on my training",
]

# Patterns for unsupported claims
UNSUPPORTED_CLAIMS = [
    r"guaranteed?\s+to",
    r"will\s+definitely",
    r"100%\s+(?:sure|certain|accurate)",
    r"without\s+a\s+doubt",
]


class OutputGuard:
    """Output validation and safety checks."""

    @staticmethod
    def check_hallucination(text: str) -> list[str]:
        """Check for potential hallucination indicators."""
        found = []
        text_lower = text.lower()
        for pattern in HALLUCINATION_PATTERNS:
            if re.search(pattern, text_lower):
                found.append(pattern)
        return found

    @staticmethod
    def check_unsupported_claims(text: str) -> list[str]:
        """Check for unsupported absolute claims."""
        found = []
        text_lower = text.lower()
        for pattern in UNSUPPORTED_CLAIMS:
            if re.search(pattern, text_lower):
                found.append(pattern)
        return found

    @staticmethod
    def check_evidence_requirement(text: str, citations: list[dict]) -> dict:
        """Check that claims are supported by evidence."""
        result = {
            "has_citations": len(citations) > 0,
            "citation_count": len(citations),
            "warnings": [],
        }

        if not citations and len(text) > 200:
            result["warnings"].append("Long response without citations")

        return result

    @classmethod
    def validate(cls, text: str, citations: list[dict]) -> dict:
        """Run all output checks."""
        result = {
            "valid": True,
            "warnings": [],
            "hallucination_indicators": cls.check_hallucination(text),
            "unsupported_claims": cls.check_unsupported_claims(text),
        }

        evidence_check = cls.check_evidence_requirement(text, citations)
        result["warnings"].extend(evidence_check["warnings"])

        if result["hallucination_indicators"]:
            result["warnings"].append("Potential hallucination indicators detected")

        if result["unsupported_claims"]:
            result["warnings"].append("Unsupported absolute claims detected")

        return result
