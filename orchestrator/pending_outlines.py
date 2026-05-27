"""Persistent outline confirmation tickets for the whole-paper workflow."""

from __future__ import annotations

import copy
import hashlib
import json
import threading
import uuid
from datetime import datetime
from pathlib import Path


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def request_fingerprint(source_request: dict) -> str:
    normalized = {
        key: str(source_request.get(key, "") or "").strip()
        for key in ("document_path", "topic", "requirements", "language")
    }
    payload = json.dumps(normalized, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class PendingOutlineStore:
    """Keep a generated outline stable until the user confirms or replaces it."""

    OPEN_STATUSES = {"waiting_confirmation", "waiting_materials", "writing"}

    def __init__(self, path: str | Path = "data/checkpoints/pending_outlines.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._records = self._load()

    def create(self, source_request: dict, outline_result: dict) -> dict:
        with self._lock:
            outline_id = f"outline-{uuid.uuid4().hex[:12]}"
            status = str(outline_result.get("status") or "waiting_confirmation")
            record = {
                "outline_id": outline_id,
                "request_fingerprint": request_fingerprint(source_request),
                "source_request": copy.deepcopy(source_request),
                "outline_result": copy.deepcopy(outline_result),
                "status": status,
                "job_id": "",
                "created_at": _now(),
                "updated_at": _now(),
            }
            self._records[outline_id] = record
            self._save()
            return copy.deepcopy(record)

    def find_open(self, source_request: dict) -> dict | None:
        fingerprint = request_fingerprint(source_request)
        with self._lock:
            candidates = [
                record
                for record in self._records.values()
                if record.get("request_fingerprint") == fingerprint
                and record.get("status") in self.OPEN_STATUSES
            ]
            if not candidates:
                return None
            record = max(candidates, key=lambda item: item.get("updated_at", ""))
            return copy.deepcopy(record)

    def find_open_by_title(self, title: str) -> dict | None:
        """Recover the same displayed outline when a client loses its ticket id."""
        normalized_title = str(title or "").strip()
        if not normalized_title:
            return None
        with self._lock:
            candidates = [
                record
                for record in self._records.values()
                if record.get("status") in self.OPEN_STATUSES
                and str(
                    (record.get("outline_result") or {}).get("outline", {}).get("title", "")
                ).strip() == normalized_title
            ]
            if not candidates:
                return None
            record = max(candidates, key=lambda item: item.get("updated_at", ""))
            return copy.deepcopy(record)

    def get(self, outline_id: str) -> dict | None:
        with self._lock:
            record = self._records.get(str(outline_id or "").strip())
            return copy.deepcopy(record) if record else None

    def latest_waiting(self) -> dict | None:
        with self._lock:
            candidates = [
                record
                for record in self._records.values()
                if record.get("status") in {"waiting_confirmation", "waiting_materials"}
            ]
            if not candidates:
                return None
            return copy.deepcopy(max(candidates, key=lambda item: item.get("updated_at", "")))

    def mark(self, outline_id: str, status: str, *, job_id: str = "") -> dict | None:
        with self._lock:
            record = self._records.get(str(outline_id or "").strip())
            if not record:
                return None
            record["status"] = status
            if job_id:
                record["job_id"] = job_id
            record["updated_at"] = _now()
            self._save()
            return copy.deepcopy(record)

    def _load(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return raw if isinstance(raw, dict) else {}

    def _save(self) -> None:
        self.path.write_text(
            json.dumps(self._records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
