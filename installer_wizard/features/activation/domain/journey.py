from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import Enum

from features.activation.domain.errors import JourneyError

SCHEMA_VERSION = 1
ERROR_LIMIT = 500


class Stage(str, Enum):
    NEW = "new"
    RUNNING = "running"
    AWAITING_USER = "awaiting_user"
    FAILED = "failed"
    DONE = "done"
    RESETTING = "resetting"


class SequenceStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    DECLINED = "declined"
    DEFERRED = "deferred"
    NOT_APPLICABLE = "not_applicable"
    SKIPPED = "skipped"
    FAILED = "failed"


SETTLED = frozenset({SequenceStatus.DONE, SequenceStatus.DECLINED, SequenceStatus.DEFERRED,
                     SequenceStatus.NOT_APPLICABLE, SequenceStatus.SKIPPED})
OPEN = frozenset({SequenceStatus.PENDING, SequenceStatus.RUNNING})


@dataclass
class SequenceProgress:
    status: SequenceStatus = SequenceStatus.PENDING
    choice: str = ""
    attempts: int = 0
    error: str = ""
    started_at: float = 0.0
    finished_at: float = 0.0

    def to_dict(self) -> dict:
        return {"status": self.status.value, "choice": self.choice, "attempts": self.attempts, "error": self.error,
                "started_at": self.started_at, "finished_at": self.finished_at}

    @classmethod
    def from_dict(cls, raw: Mapping) -> SequenceProgress:
        return cls(status=SequenceStatus(raw.get("status", SequenceStatus.PENDING.value)),
                   choice=str(raw.get("choice", "")), attempts=int(raw.get("attempts", 0)),
                   error=str(raw.get("error", ""))[:ERROR_LIMIT], started_at=float(raw.get("started_at", 0.0)),
                   finished_at=float(raw.get("finished_at", 0.0)))


@dataclass
class Journey:
    stage: Stage = Stage.NEW
    order: list[str] = field(default_factory=list)
    progress: dict[str, SequenceProgress] = field(default_factory=dict)
    current: str = ""
    revision: int = 0
    created_at: float = 0.0
    updated_at: float = 0.0

    @classmethod
    def new(cls, now: float) -> Journey:
        return cls(created_at=now, updated_at=now)

    @property
    def choices(self) -> dict[str, str]:
        return {sid: rec.choice for sid, rec in self.progress.items() if rec.choice}

    @property
    def started(self) -> bool:
        return self.stage is not Stage.NEW

    def next_open(self) -> str | None:
        return next((sid for sid in self.order if self.progress[sid].status in OPEN), None)

    def percent(self) -> float:
        if not self.order:
            return 0.0
        settled = sum(1 for sid in self.order if self.progress[sid].status in SETTLED)
        return round(settled * 100 / len(self.order), 1)

    def expect_revision(self, revision: int) -> None:
        if revision != self.revision:
            raise JourneyError("journey.stale_revision", expected=self.revision, received=revision)

    def start(self, sequence_ids: Iterable[str], now: float) -> None:
        self._require(Stage.NEW)
        ids = list(sequence_ids)
        if not ids or len(set(ids)) != len(ids):
            raise JourneyError("journey.invalid_sequence_list")
        self.order = ids
        self.progress = {sid: SequenceProgress() for sid in ids}
        self.stage = Stage.RUNNING
        self._commit(now)

    def begin(self, sequence_id: str, now: float) -> None:
        self._require(Stage.RUNNING)
        rec = self._open(sequence_id)
        rec.status = SequenceStatus.RUNNING
        rec.attempts += 1
        rec.error = ""
        rec.started_at = now
        self.current = sequence_id
        self._commit(now)

    def complete(self, sequence_id: str, now: float) -> None:
        self._require(Stage.RUNNING)
        self._settle(self._running(sequence_id), SequenceStatus.DONE, now)

    def mark_not_applicable(self, sequence_id: str, now: float) -> None:
        self._require(Stage.RUNNING)
        rec = self._record(sequence_id)
        if rec.status is not SequenceStatus.PENDING:
            raise JourneyError("journey.sequence_not_pending", sequence=sequence_id)
        self._settle(rec, SequenceStatus.NOT_APPLICABLE, now)

    def await_user(self, sequence_id: str, now: float) -> None:
        self._require(Stage.RUNNING)
        rec = self._record(sequence_id)
        if rec.status is not SequenceStatus.PENDING or rec.choice:
            raise JourneyError("journey.sequence_not_pending", sequence=sequence_id)
        self.stage = Stage.AWAITING_USER
        self.current = sequence_id
        self._commit(now)

    def choose(self, sequence_id: str, choice_id: str, installs: bool, now: float) -> None:
        rec = self._awaited(sequence_id)
        rec.choice = choice_id
        self.stage = Stage.RUNNING
        if installs:
            self._commit(now)
            return
        self._settle(rec, SequenceStatus.DECLINED, now)

    def submit(self, sequence_id: str, now: float) -> None:
        rec = self._awaited(sequence_id)
        self.stage = Stage.RUNNING
        self._settle(rec, SequenceStatus.DONE, now)

    def defer(self, sequence_id: str, skippable: bool, now: float) -> None:
        if not skippable:
            raise JourneyError("journey.sequence_not_skippable", sequence=sequence_id)
        rec = self._awaited(sequence_id)
        self.stage = Stage.RUNNING
        self._settle(rec, SequenceStatus.DEFERRED, now)

    def fail(self, sequence_id: str, error_code: str, now: float) -> None:
        self._require(Stage.RUNNING)
        rec = self._running(sequence_id)
        rec.status = SequenceStatus.FAILED
        rec.error = error_code[:ERROR_LIMIT]
        rec.finished_at = now
        self.stage = Stage.FAILED
        self.current = sequence_id
        self._commit(now)

    def retry(self, sequence_id: str, now: float) -> None:
        rec = self._failed(sequence_id)
        rec.status = SequenceStatus.PENDING
        self.stage = Stage.RUNNING
        self._commit(now)

    def skip(self, sequence_id: str, critical: bool, now: float) -> None:
        if critical:
            raise JourneyError("journey.sequence_critical", sequence=sequence_id)
        rec = self._failed(sequence_id)
        self.stage = Stage.RUNNING
        self._settle(rec, SequenceStatus.SKIPPED, now)

    def finish(self, now: float) -> None:
        self._require(Stage.RUNNING)
        if any(self.progress[sid].status not in SETTLED for sid in self.order):
            raise JourneyError("journey.unsettled_sequences")
        self.stage = Stage.DONE
        self.current = ""
        self._commit(now)

    def request_reset(self, now: float) -> None:
        if self.stage is Stage.RESETTING:
            return
        self.stage = Stage.RESETTING
        self._commit(now)

    def _require(self, *stages: Stage) -> None:
        if self.stage not in stages:
            raise JourneyError("journey.stage_not_allowed", stage=self.stage.value,
                               expected=",".join(s.value for s in stages))

    def _record(self, sequence_id: str) -> SequenceProgress:
        rec = self.progress.get(sequence_id)
        if rec is None:
            raise JourneyError("journey.unknown_sequence", sequence=sequence_id)
        return rec

    def _open(self, sequence_id: str) -> SequenceProgress:
        rec = self._record(sequence_id)
        if rec.status not in OPEN:
            raise JourneyError("journey.sequence_settled", sequence=sequence_id, status=rec.status.value)
        return rec

    def _running(self, sequence_id: str) -> SequenceProgress:
        rec = self._record(sequence_id)
        if rec.status is not SequenceStatus.RUNNING:
            raise JourneyError("journey.sequence_not_running", sequence=sequence_id)
        return rec

    def _failed(self, sequence_id: str) -> SequenceProgress:
        self._require(Stage.FAILED)
        rec = self._record(sequence_id)
        if rec.status is not SequenceStatus.FAILED:
            raise JourneyError("journey.sequence_not_failed", sequence=sequence_id)
        return rec

    def _awaited(self, sequence_id: str) -> SequenceProgress:
        self._require(Stage.AWAITING_USER)
        if sequence_id != self.current:
            raise JourneyError("journey.sequence_not_awaited", sequence=sequence_id)
        return self._record(sequence_id)

    def _settle(self, rec: SequenceProgress, status: SequenceStatus, now: float) -> None:
        rec.status = status
        rec.finished_at = now
        self.current = ""
        self._commit(now)

    def _commit(self, now: float) -> None:
        self.revision += 1
        self.updated_at = now

    def to_dict(self) -> dict:
        return {"schema_version": SCHEMA_VERSION, "stage": self.stage.value, "order": list(self.order),
                "progress": {sid: rec.to_dict() for sid, rec in self.progress.items()}, "current": self.current,
                "percent": self.percent(), "revision": self.revision, "created_at": self.created_at,
                "updated_at": self.updated_at}

    @classmethod
    def from_dict(cls, raw: Mapping) -> Journey:
        if raw.get("schema_version") != SCHEMA_VERSION:
            raise JourneyError("journey.unsupported_schema", value=raw.get("schema_version"))
        order = [str(sid) for sid in raw.get("order", [])]
        if len(set(order)) != len(order):
            raise JourneyError("journey.invalid_sequence_list")
        stored = raw.get("progress", {})
        journey = cls(stage=Stage(raw.get("stage", Stage.NEW.value)), order=order,
                      progress={sid: SequenceProgress.from_dict(stored.get(sid, {})) for sid in order},
                      current=str(raw.get("current", "")), revision=int(raw.get("revision", 0)),
                      created_at=float(raw.get("created_at", 0.0)), updated_at=float(raw.get("updated_at", 0.0)))
        if journey.current and journey.current not in journey.progress:
            raise JourneyError("journey.unknown_sequence", sequence=journey.current)
        return journey
