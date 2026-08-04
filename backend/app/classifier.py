"""Load the multi-class topic model and produce routing decisions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib

ACCEPTED_TOPICS = frozenset({"cloud_computing", "telecommunications"})

TOPIC_DISPLAY = {
    "cloud_computing": "cloud computing",
    "telecommunications": "telecommunications",
    "cybersecurity": "cybersecurity",
    "consumer_electronics": "consumer electronics",
    "enterprise_software": "enterprise software",
    "financial_services": "financial services",
    "healthcare": "healthcare",
    "retail_ecommerce": "retail and ecommerce",
    "transportation_logistics": "transportation and logistics",
    "energy": "energy",
}


def resolve_model_path() -> Path:
    """Resolve path to ml_multi_v1.joblib relative to the repo root."""
    here = Path(__file__).resolve()
    repo_root = here.parents[2]
    return repo_root / "data" / "models" / "ml_multi_v1.joblib"


def topic_label(topic: str) -> str:
    return TOPIC_DISPLAY.get(topic, topic.replace("_", " "))


@dataclass
class Prediction:
    topic: str
    topic_label: str
    status: str  # "accepted" | "quarantined"
    message: str
    confidence: float


class TopicClassifier:
    def __init__(self, model_path: Path | None = None) -> None:
        path = model_path or resolve_model_path()
        if not path.is_file():
            raise FileNotFoundError(f"Model not found at {path}")
        self.model: Any = joblib.load(path)
        self.model_path = path
        clf = self.model.named_steps["clf"]
        self.classes_: list[str] = list(clf.classes_)

    def predict(self, article_text: str) -> Prediction:
        text = article_text.strip()
        if not text:
            raise ValueError("Article text is empty.")

        topic = str(self.model.predict([text])[0])
        proba = self.model.predict_proba([text])[0]
        class_index = self.classes_.index(topic)
        confidence = float(proba[class_index])
        label = topic_label(topic)

        if topic in ACCEPTED_TOPICS:
            status = "accepted"
            message = (
                f"This file is about {label} and has been accepted to the Doc Center."
            )
        else:
            status = "quarantined"
            message = (
                f"This file is about {label} and has been moved to Quarantine. "
                "You should upload files about cloud computing and telecommunications only."
            )

        return Prediction(
            topic=topic,
            topic_label=label,
            status=status,
            message=message,
            confidence=confidence,
        )
