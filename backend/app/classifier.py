"""Load the multi-class topic model and produce routing decisions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np

# OOF-selected max-proba threshold from ml_multi_v1 (coverage ≥ 70%).
DEFAULT_TAU = 0.26

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
class TokenContribution:
    token: str
    tfidf: float
    coef: float
    contribution: float


@dataclass
class Prediction:
    topic: str
    topic_label: str
    status: str  # "accepted" | "quarantined" | "needs_review"
    message: str
    confidence: float
    contributions: list[TokenContribution]


class TopicClassifier:
    def __init__(self, model_path: Path | None = None) -> None:
        path = model_path or resolve_model_path()
        if not path.is_file():
            raise FileNotFoundError(f"Model not found at {path}")
        self.model: Any = joblib.load(path)
        self.model_path = path
        self.tfidf = self.model.named_steps["tfidf"]
        self.clf = self.model.named_steps["clf"]
        self.classes_: list[str] = list(self.clf.classes_)
        self.feature_names = np.asarray(self.tfidf.get_feature_names_out())

    def explain(self, article_text: str, topic: str, top_k: int = 10) -> list[TokenContribution]:
        class_index = self.classes_.index(topic)
        x = self.tfidf.transform([article_text])
        coefs = np.asarray(self.clf.coef_[class_index]).ravel()
        x_dense = np.asarray(x.todense()).ravel()
        contrib = x_dense * coefs
        nz = np.flatnonzero(x_dense)
        if len(nz) == 0:
            return []
        order = nz[np.argsort(np.abs(contrib[nz]))[::-1][:top_k]]
        return [
            TokenContribution(
                token=str(self.feature_names[i]),
                tfidf=float(x_dense[i]),
                coef=float(coefs[i]),
                contribution=float(contrib[i]),
            )
            for i in order
        ]

    def predict(self, article_text: str, tau: float = DEFAULT_TAU) -> Prediction:
        text = article_text.strip()
        if not text:
            raise ValueError("Article text is empty.")

        topic = str(self.model.predict([text])[0])
        proba = self.model.predict_proba([text])[0]
        class_index = self.classes_.index(topic)
        confidence = float(proba[class_index])
        label = topic_label(topic)
        contributions = self.explain(text, topic)

        if confidence < tau:
            status = "needs_review"
            message = (
                f"This file may be about {label}, but confidence "
                f"({confidence:.0%}) is below the review threshold ({tau:.0%}). "
                "It has been sent to Needs review."
            )
        elif topic in ACCEPTED_TOPICS:
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
            contributions=contributions,
        )
