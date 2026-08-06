"""In-memory session store for Doc Center, Needs review, and Quarantine."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass
class TokenContribution:
    token: str
    tfidf: float
    coef: float
    contribution: float


@dataclass
class RoutedFile:
    id: str
    filename: str
    topic: str
    topic_label: str
    status: str
    confidence: float
    article_text: str
    routed_at: str
    decision_source: str = "auto"  # auto | reviewer:accept | reviewer:reject
    contributions: list[TokenContribution] = field(default_factory=list)
    reviewed_at: str | None = None

    def to_list_item(self) -> dict:
        return {
            "id": self.id,
            "filename": self.filename,
            "topic": self.topic,
            "topic_label": self.topic_label,
            "status": self.status,
            "confidence": round(self.confidence, 4),
            "routed_at": self.routed_at,
            "decision_source": self.decision_source,
            "reviewed_at": self.reviewed_at,
        }

    def to_detail(self) -> dict:
        return {
            **self.to_list_item(),
            "article_text": self.article_text,
            "contributions": [asdict(c) for c in self.contributions],
        }


class FileStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._by_id: dict[str, RoutedFile] = {}
        self._doc_center: list[str] = []
        self._needs_review: list[str] = []
        self._quarantine: list[str] = []

    def _bucket(self, status: str) -> list[str]:
        if status == "accepted":
            return self._doc_center
        if status == "needs_review":
            return self._needs_review
        if status == "quarantined":
            return self._quarantine
        raise ValueError(f"Unknown status: {status}")

    def add(
        self,
        *,
        filename: str,
        topic: str,
        topic_label: str,
        status: str,
        confidence: float,
        article_text: str,
        contributions: list[TokenContribution] | None = None,
        decision_source: str = "auto",
    ) -> RoutedFile:
        entry = RoutedFile(
            id=uuid4().hex[:12],
            filename=filename,
            topic=topic,
            topic_label=topic_label,
            status=status,
            confidence=confidence,
            article_text=article_text,
            routed_at=_now(),
            decision_source=decision_source,
            contributions=contributions or [],
        )
        with self._lock:
            self._by_id[entry.id] = entry
            self._bucket(status).insert(0, entry.id)
        return entry

    def get(self, file_id: str) -> RoutedFile | None:
        with self._lock:
            return self._by_id.get(file_id)

    def list_all(self) -> dict:
        with self._lock:
            return {
                "doc_center": [self._by_id[i].to_list_item() for i in self._doc_center],
                "needs_review": [
                    self._by_id[i].to_list_item() for i in self._needs_review
                ],
                "quarantine": [self._by_id[i].to_list_item() for i in self._quarantine],
            }

    def move(
        self,
        file_id: str,
        *,
        new_status: str,
        decision_source: str,
    ) -> RoutedFile:
        with self._lock:
            entry = self._by_id.get(file_id)
            if entry is None:
                raise KeyError(file_id)
            if entry.status != "needs_review":
                raise ValueError("Only files in Needs review can be accepted or rejected.")
            self._needs_review.remove(file_id)
            entry.status = new_status
            entry.decision_source = decision_source
            entry.reviewed_at = _now()
            self._bucket(new_status).insert(0, file_id)
            return entry

    def clear(self) -> None:
        with self._lock:
            self._by_id.clear()
            self._doc_center.clear()
            self._needs_review.clear()
            self._quarantine.clear()
