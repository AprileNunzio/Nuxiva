from __future__ import annotations

import time

from features.activation.domain.journey import Journey
from features.activation.infrastructure.journey_store import JourneyStore


class ResetJourneyUseCase:
    def __init__(self, store: JourneyStore) -> None:
        self._store = store

    def execute(self) -> Journey:
        now = time.time()
        journey = self._store.load()
        if journey is None:
            journey = Journey.new(now)
            self._store.save(journey)
            return journey

        journey.request_reset(now)
        self._store.save(journey)
        return journey
