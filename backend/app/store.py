"""In-memory session lists for Doc Center and Quarantine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4


@dataclass
class RoutedFile:
    id: str
    filename: str
    topic: str
    topic_label: str
    status: str
    routed_at: str

    def to_list_item(self) -> dict:
        return {
            "id": self.id,
            "filename": self.filename,
            "topic": self.topic,
            "topic_label": self.topic_label,
            "routed_at": self.routed_at,
        }


class FileStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._doc_center: list[RoutedFile] = []
        self._quarantine: list[RoutedFile] = []

    def add(
        self,
        *,
        filename: str,
        topic: str,
        topic_label: str,
        status: str,
    ) -> RoutedFile:
        entry = RoutedFile(
            id=uuid4().hex[:12],
            filename=filename,
            topic=topic,
            topic_label=topic_label,
            status=status,
            routed_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        )
        with self._lock:
            if status == "accepted":
                self._doc_center.insert(0, entry)
            else:
                self._quarantine.insert(0, entry)
        return entry

    def list_all(self) -> dict:
        with self._lock:
            return {
                "doc_center": [e.to_list_item() for e in self._doc_center],
                "quarantine": [e.to_list_item() for e in self._quarantine],
            }

    def clear(self) -> None:
        with self._lock:
            self._doc_center.clear()
            self._quarantine.clear()
