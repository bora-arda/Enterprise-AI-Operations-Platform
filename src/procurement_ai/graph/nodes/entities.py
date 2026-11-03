"""Entity detection and clarification helpers."""

import re

INVOICE_RE = re.compile(r"\b(INV-\d+)\b", re.IGNORECASE)
PO_RE = re.compile(r"\b(PO-\d+)\b", re.IGNORECASE)
CONTRACT_RE = re.compile(r"\b(CF-\d{4}-\d+)\b", re.IGNORECASE)
PAYMENT_RE = re.compile(r"\b(PAY-[A-Z0-9-]+)\b", re.IGNORECASE)
APPROVAL_RE = re.compile(r"\b(APPR-[A-Z0-9]+)\b", re.IGNORECASE)

ENTITY_PATTERNS = [INVOICE_RE, PO_RE, CONTRACT_RE, PAYMENT_RE, APPROVAL_RE]

LOOKUP_CUES = re.compile(
    r"\b(status|details?|show|info|about|what\s+is|where\s+is|display|view|look\s*up)\b",
    re.IGNORECASE,
)
BROAD_QUERY_CUES = re.compile(
    r"\b(which|list|all|overdue|duplicate|violat|spend|spending|top|average|"
    r"trend|policy|policies|process|terms|expire|expiring|outstanding|"
    r"request\s+payment|find\s+transactions|exceed|most|report|summar)\b",
    re.IGNORECASE,
)

ENTITY_WORDS = {
    "invoice": (r"\binvoice\b", "invoice number (for example INV-000010)"),
    "purchase order": (
        r"\b(purchase\s+order|p\.?o\.?)\b",
        "purchase order number (for example PO-000005)",
    ),
    "contract": (r"\bcontract\b", "contract number (for example CF-2022-00011)"),
    "payment": (r"\bpayment\b", "payment reference (for example PAY-000007)"),
    "approval": (r"\bapproval\b", "approval reference (for example APPR-2F0BD54B)"),
}


def has_entity_id(text: str) -> bool:
    """Return True if the text contains any supported entity identifier."""
    return any(pattern.search(text) for pattern in ENTITY_PATTERNS)


def extract_entity_id(text: str) -> tuple[str, str] | None:
    """Return (entity_type, identifier) for the first identifier found."""
    for entity_type, pattern in (
        ("invoice", INVOICE_RE),
        ("purchase_order", PO_RE),
        ("contract", CONTRACT_RE),
        ("payment", PAYMENT_RE),
        ("approval", APPROVAL_RE),
    ):
        match = pattern.search(text)
        if match:
            return entity_type, match.group(1).upper()
    return None


def clarification_message(text: str) -> str | None:
    """
    Return a clarification prompt if the question looks like an entity lookup
    but lacks an identifier. Broad/list/analytics questions never clarify.
    """
    if has_entity_id(text) or BROAD_QUERY_CUES.search(text):
        return None
    if not LOOKUP_CUES.search(text):
        return None

    # Plural entity nouns indicate list questions, not single-record lookups.
    if re.search(
        r"\b(invoices|purchase\s+orders|contracts|payments|approvals|vendors|suppliers)\b",
        text,
        re.IGNORECASE,
    ):
        return None

    for entity, (pattern, hint) in ENTITY_WORDS.items():
        if re.search(pattern, text, re.IGNORECASE):
            return f"I can look up that {entity}, but I need the {hint}. Which {entity} would you like to see?"

    if re.search(r"\b(vendors?|suppliers?)\b", text, re.IGNORECASE):
        return "I can look up a vendor, but I need the vendor name (for example, a name from your supplier list)."

    return None


def extract_vendor_name(text: str) -> str | None:
    """Extract a vendor name from patterns like 'vendor Acme Ltd' or quotes."""
    quoted = re.search(r"[\"']([^\"']{2,80})[\"']", text)
    if quoted:
        return quoted.group(1).strip()

    match = re.search(
        r"\b(?:vendor|supplier)\s+(?:named\s+|called\s+)?"
        r"([A-Za-z0-9][A-Za-z0-9&.,'\- ]{1,60})",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None

    name = match.group(1).strip(" .,?")
    # Trim trailing filler words
    name = re.split(
        r"\s+(?:status|details?|information|info|please|now|today|"
        r"payment\s+terms?|contracts?|invoices?)\b",
        name,
        flags=re.IGNORECASE,
    )[0].strip(" .,?")
    return name or None
