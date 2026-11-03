"""Business metrics evaluation for anomaly detection."""

import logging

logger = logging.getLogger(__name__)


def anomaly_precision(detected: list[str], ground_truth: list[str]) -> float:
    """Compute anomaly detection precision."""
    if not detected:
        return 0.0
    detected_set = set(detected)
    truth_set = set(ground_truth)
    return len(detected_set & truth_set) / len(detected_set)


def anomaly_recall(detected: list[str], ground_truth: list[str]) -> float:
    """Compute anomaly detection recall."""
    if not ground_truth:
        return 0.0
    detected_set = set(detected)
    truth_set = set(ground_truth)
    return len(detected_set & truth_set) / len(truth_set)


def false_positive_rate(detected: list[str], ground_truth: list[str], total_normal: int) -> float:
    """Compute false positive rate."""
    if total_normal == 0:
        return 0.0
    detected_set = set(detected)
    truth_set = set(ground_truth)
    false_positives = len(detected_set - truth_set)
    return false_positives / total_normal


def evaluate_business(
    ground_truth: list[dict],
    detected: list[dict],
) -> dict[str, float]:
    """Evaluate business metrics for anomaly detection."""
    truth_ids = {item["entity_id"] for item in ground_truth}
    detected_ids = {item["entity_id"] for item in detected}

    precision = anomaly_precision(list(detected_ids), list(truth_ids))
    recall = anomaly_recall(list(detected_ids), list(truth_ids))

    # Estimate total normal records
    total_normal = 500  # Placeholder - should come from actual data
    fpr = false_positive_rate(list(detected_ids), list(truth_ids), total_normal)

    return {
        "anomaly_precision": precision,
        "anomaly_recall": recall,
        "false_positive_rate": fpr,
        "total_ground_truth": len(truth_ids),
        "total_detected": len(detected_ids),
    }
