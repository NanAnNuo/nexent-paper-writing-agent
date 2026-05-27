"""Background write-job state used to keep long paper generation resumable."""

from __future__ import annotations

import copy
import json
import uuid
from datetime import datetime
from pathlib import Path


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class WriteJobStore:
    """Persist short job snapshots while the async task runs in the MCP process."""

    def __init__(self, path: str | Path = "data/checkpoints/write_jobs.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._jobs = self._load()

    def create(
        self,
        title: str = "",
        section_count: int = 0,
        *,
        job_kind: str = "paper",
        snapshot: dict | None = None,
    ) -> dict:
        job_prefix = "section" if job_kind == "section" else "write"
        job_id = f"{job_prefix}-{uuid.uuid4().hex[:12]}"
        job = {
            "job_id": job_id,
            "job_kind": job_kind,
            "status": "accepted",
            "result_status": "",
            "title": title or "untitled",
            "section_count": section_count,
            "progress": {"current": 0, "total": section_count or None, "message": "accepted"},
            "events": [{"timestamp": _now(), "message": f"{job_kind} job accepted"}],
            "result": None,
            "snapshot": copy.deepcopy(snapshot or {}),
            "error": "",
            "created_at": _now(),
            "updated_at": _now(),
        }
        self._jobs[job_id] = job
        self._save()
        return copy.deepcopy(job)

    def mark_running(self, job_id: str) -> None:
        self._update(job_id, status="running")
        self.add_event(job_id, f"{self._jobs[job_id].get('job_kind', 'write')} job running")

    def record_progress(
        self,
        job_id: str,
        *,
        progress: float,
        total: float | None = None,
        message: str = "",
    ) -> None:
        job = self._jobs[job_id]
        job["progress"] = {
            "current": progress,
            "total": total,
            "message": message or job.get("progress", {}).get("message", ""),
        }
        job["updated_at"] = _now()
        if message:
            self._append_event(job, message)
        self._save()

    def add_event(self, job_id: str, message: str) -> None:
        job = self._jobs[job_id]
        self._append_event(job, message)
        job["updated_at"] = _now()
        self._save()

    def finish(self, job_id: str, result: dict) -> None:
        result_status = str(result.get("status", "completed"))
        final_status = (
            "completed"
            if result_status in {"completed", "success"}
            else "finished_with_blocker"
        )
        self._update(job_id, status=final_status, result_status=result_status, result=result)
        self.add_event(job_id, f"{self._jobs[job_id].get('job_kind', 'write')} job finished with status {result_status}")

    def fail(self, job_id: str, error: str) -> None:
        self._update(job_id, status="failed", result_status="error", error=error)
        self.add_event(job_id, f"{self._jobs[job_id].get('job_kind', 'write')} job failed: {error}")

    def get(self, job_id: str, event_limit: int | None = None) -> dict | None:
        job = self._jobs.get(job_id)
        if not job:
            return None
        snapshot = copy.deepcopy(job)
        if event_limit is not None:
            snapshot["events"] = snapshot.get("events", [])[-max(0, event_limit):]
        return snapshot

    def summaries(self) -> list[dict]:
        fields = (
            "job_id", "job_kind", "status", "result_status", "title",
            "progress", "created_at", "updated_at",
        )
        return [{field: copy.deepcopy(job.get(field)) for field in fields} for job in self._jobs.values()]

    def _append_event(self, job: dict, message: str) -> None:
        events = job.setdefault("events", [])
        if events and events[-1].get("message") == message:
            return
        events.append({"timestamp": _now(), "message": message})
        del events[:-100]

    def _update(self, job_id: str, **values) -> None:
        job = self._jobs[job_id]
        job.update(values)
        job["updated_at"] = _now()
        self._save()

    def _load(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if isinstance(raw, dict):
            return raw
        return {}

    def _save(self) -> None:
        self.path.write_text(json.dumps(self._jobs, ensure_ascii=False, indent=2), encoding="utf-8")


class WriteJobProgressContext:
    """Subset of the FastMCP Context API used by the writer heartbeat."""

    def __init__(self, store: WriteJobStore, job_id: str):
        self.store = store
        self.job_id = job_id

    async def report_progress(self, progress, total=None, message=None):
        self.store.record_progress(
            self.job_id,
            progress=progress,
            total=total,
            message=message or "",
        )

    async def info(self, message):
        self.store.add_event(self.job_id, str(message))
