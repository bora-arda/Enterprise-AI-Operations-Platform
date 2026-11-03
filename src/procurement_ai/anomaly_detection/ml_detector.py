"""ML-based anomaly detection using Isolation Forest."""

import logging
import pickle
from pathlib import Path

import numpy as np
from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)


class MLAnomalyDetector:
    """Isolation Forest based anomaly detector."""

    def __init__(self, contamination: float = 0.05, model_path: Path | None = None):
        self.contamination = contamination
        self.model_path = model_path
        self.model: IsolationForest | None = None

    def train(self, features: np.ndarray) -> None:
        """Train the Isolation Forest model."""
        self.model = IsolationForest(
            contamination=self.contamination,
            random_state=42,
        )
        self.model.fit(features)
        logger.info(f"Trained Isolation Forest on {len(features)} samples")

    def predict(self, features: np.ndarray) -> list[bool]:
        """Predict anomalies. True = anomaly."""
        if not self.model:
            raise RuntimeError("Model not trained")
        predictions = self.model.predict(features)
        return predictions == -1  # -1 indicates anomaly

    def save(self, path: Path | None = None) -> None:
        """Save the trained model."""
        path = path or self.model_path
        if not path or not self.model:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self.model, f)
        logger.info(f"Saved model to {path}")

    def load(self, path: Path | None = None) -> None:
        """Load a trained model."""
        path = path or self.model_path
        if not path or not path.exists():
            return
        with open(path, "rb") as f:
            self.model = pickle.load(f)
        logger.info(f"Loaded model from {path}")
