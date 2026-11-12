from __future__ import annotations

import time
from collections.abc import Callable

from agenti.activation.domain.errors import JourneyError
from agenti.activation.domain.journey import Journey, SequenceStatus, Stage
from agenti.activation.domain.sequence import SequenceKind
from agenti.activation.domain.telemetry import TelemetrySnapshot
from agenti.activation.infrastructure.journey_store import JourneyStore
from agenti.activation.infrastructure.sequence_catalog import SequenceCatalog
from agenti.activation.infrastructure.step_runner import StepRunner


class AdvanceJourneyUseCase:
    def __init__(
        self,
        store: JourneyStore,
        catalog: SequenceCatalog,
        step_runner: StepRunner,
        write_env_fn: Callable[[dict[str, str]], None],
    ) -> None:
        self._store = store
        self._catalog = catalog
        self._step_runner = step_runner
        self._write_env = write_env_fn

    async def execute(
        self,
        on_telemetry: Callable[[str, TelemetrySnapshot], None] | None = None,
    ) -> Journey:
        journey = self._store.load()
        if journey is None:
            raise JourneyError("journey.not_found")

        if journey.stage == Stage.FAILED and journey.current:
            seq = self._catalog.get(journey.current)
            rec = journey.progress.get(journey.current)
            if seq and rec:
                if not seq.critical:
                    journey.skip(journey.current, False, time.time())
                    self._store.save(journey)
                elif rec.attempts < 3:
                    journey.retry(journey.current, time.time())
                    self._store.save(journey)

        if journey.stage == Stage.NEW:
            journey.stage = Stage.RUNNING
            self._store.save(journey)

        if journey.stage not in (Stage.RUNNING, Stage.AWAITING_USER):
            return journey

        while journey.stage == Stage.RUNNING:
            next_id = journey.next_open()
            if next_id is None:
                journey.finish(time.time())
                self._store.save(journey)
                break

            seq = self._catalog.get(next_id)
            if seq is None:
                raise JourneyError("journey.unknown_sequence", sequence=next_id)

            rec = journey.progress[next_id]

            if seq.kind == SequenceKind.OPTIONAL and not rec.choice:
                journey.await_user(next_id, time.time())
                self._store.save(journey)
                return journey

            if seq.kind == SequenceKind.CONFIGURE and rec.status != "done":
                journey.await_user(next_id, time.time())
                self._store.save(journey)
                return journey

            if seq.kind == SequenceKind.OPTIONAL and rec.choice:
                choice = seq.choice(rec.choice)
                if not choice.installs:
                    rec.status = SequenceStatus.DECLINED
                    self._store.save(journey)
                    continue
                if choice.env:
                    self._write_env(dict(choice.env))

            if seq.env:
                self._write_env(dict(seq.env))

            journey.begin(next_id, time.time())
            self._store.save(journey)

            failed = False
            for step_id in seq.steps:
                def cb(snap: TelemetrySnapshot) -> None:
                    if on_telemetry:
                        on_telemetry(step_id, snap)

                code, err = await self._step_runner.execute_step(step_id, "apply", cb)
                if code != 0:
                    if not seq.critical:
                        journey.skip(next_id, False, time.time())
                        self._store.save(journey)
                        failed = True
                        break
                    else:
                        journey.fail(next_id, err or f"step {step_id} exit {code}", time.time())
                        self._store.save(journey)
                        failed = True
                        break

            if not failed:
                journey.complete(next_id, time.time())
                self._store.save(journey)

        return journey
