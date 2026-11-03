"""Entity and metadata extraction from documents."""

import logging
import re

logger = logging.getLogger(__name__)


class MetadataExtractor:
    """Extract metadata and entities from documents."""

    @staticmethod
    def extract_contract_value(text: str) -> float | None:
        """Extract contract value from text."""
        patterns = [
            r"(?:value|amount|total)[^\d]*([\d,]+\.?\d*)",
            r"[£$€]([\d,]+\.?\d*)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1).replace(",", ""))
                except ValueError:
                    continue
        return None

    @staticmethod
    def extract_dates(text: str) -> list[str]:
        """Extract dates from text."""
        patterns = [
            r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",
            r"\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}",
            r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}",
        ]
        dates = []
        for pattern in patterns:
            dates.extend(re.findall(pattern, text, re.IGNORECASE))
        return dates

    @staticmethod
    def extract_payment_terms(text: str) -> str | None:
        """Extract payment terms from text."""
        patterns = [
            r"(Net[- ]?\d+)",
            r"payment\s+terms?[:\s]+([^\.]+)",
            r"(\d+)\s+days?",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def extract_parties(text: str) -> dict[str, list[str]]:
        """Extract party names from text."""
        # Simple extraction based on common patterns
        parties = {"buyers": [], "suppliers": []}

        buyer_match = re.search(r"(?:Buyer|Buyer:)[^\n]*", text, re.IGNORECASE)
        if buyer_match:
            parties["buyers"].append(buyer_match.group(0).split(":")[-1].strip())

        supplier_match = re.search(r"(?:Supplier|Supplier:)[^\n]*", text, re.IGNORECASE)
        if supplier_match:
            parties["suppliers"].append(supplier_match.group(0).split(":")[-1].strip())

        return parties
