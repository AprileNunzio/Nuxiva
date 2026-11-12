from __future__ import annotations

import time

from features.activation.domain.errors import JourneyError
from features.activation.domain.journey import Journey
from features.activation.infrastructure.journey_store import JourneyStore
from features.activation.infrastructure.sequence_catalog import SequenceCatalog


class SubmitChoiceUseCase:
    def __init__(self, store: JourneyStore, catalog: SequenceCatalog) -> None:
        self._store = store
        self._catalog = catalog

    def execute(self, sequence_id: str, choice_id: str) -> Journey:
        now = time.time()
        journey = self._store.load()
        if journey is None:
            raise JourneyError("journey.not_found")

        seq = self._catalog.get(sequence_id)
        if seq is None:
            raise JourneyError("journey.unknown_sequence", sequence=sequence_id)

        choice = seq.choice(choice_id)
        journey.choose(sequence_id, choice.id, choice.installs, now)
        self._store.save(journey)
        return journey
