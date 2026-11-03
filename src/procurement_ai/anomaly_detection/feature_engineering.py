"""Feature engineering for ML anomaly detection."""

import logging
from datetime import date

import numpy as np

logger = logging.getLogger(__name__)


def extract_features(invoices: list[dict], pos: dict, contracts: dict) -> np.ndarray:
    """Extract numerical features from invoices for ML anomaly detection."""
    features = []

    for inv in invoices:
        po = pos.get(inv.get("po_id"))
        contract = contracts.get(po.get("contract_id")) if po else None

        # Feature 1: Invoice amount (normalized)
        amount = inv.get("amount", 0)

        # Feature 2: Days since invoice date
        days_since_invoice = 0
        if inv.get("invoice_date"):
            try:
                inv_date = date.fromisoformat(inv["invoice_date"])
                days_since_invoice = (date.today() - inv_date).days
            except (ValueError, TypeError):
                pass

        # Feature 3: Days past due date
        days_past_due = 0
        if inv.get("due_date"):
            try:
                due_date = date.fromisoformat(inv["due_date"])
                days_past_due = max(0, (date.today() - due_date).days)
            except (ValueError, TypeError):
                pass

        # Feature 4: Amount ratio (invoice / PO amount)
        amount_ratio = 1.0
        if po and po.get("total_amount") and po["total_amount"] > 0:
            amount_ratio = amount / po["total_amount"]

        # Feature 5: Contract utilization ratio
        contract_utilization = 0.0
        if contract and contract.get("max_value") and contract["max_value"] > 0:
            contract_utilization = amount / contract["max_value"]

        features.append(
            [
                amount,
                days_since_invoice,
                days_past_due,
                amount_ratio,
                contract_utilization,
            ]
        )

    return np.array(features)
