from __future__ import annotations

import json
from pathlib import Path

from features.activation.domain.errors import SequenceError
from features.activation.domain.sequence import Sequence


class SequenceCatalog:
    def __init__(self, directory: Path) -> None:
        self._directory = directory
        self._sequences: dict[str, Sequence] = {}
        self.scan()

    def scan(self) -> dict[str, Sequence]:
        sequences: dict[str, Sequence] = {}
        if not self._directory.is_dir():
            return sequences

        for manifest_path in sorted(self._directory.glob("*/sequence.json")):
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
                seq = Sequence.from_manifest(data)
                if seq.id != manifest_path.parent.name:
                    raise SequenceError("sequence.folder_id_mismatch", folder=manifest_path.parent.name, seq_id=seq.id)
                sequences[seq.id] = seq
            except (OSError, ValueError, SequenceError) as exc:
                raise SequenceError("sequence.scan_failed", file=str(manifest_path), error=str(exc)) from exc

        self._sequences = sequences
        return dict(self._sequences)

    def get(self, sequence_id: str) -> Sequence | None:
        if not self._sequences:
            self.scan()
        return self._sequences.get(sequence_id)

    def ordered(self) -> list[Sequence]:
        if not self._sequences:
            self.scan()
        return sorted(self._sequences.values(), key=lambda s: s.order)
