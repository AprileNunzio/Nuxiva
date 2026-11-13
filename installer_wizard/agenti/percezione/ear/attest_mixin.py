import time

import numpy as np

RATE = 16000
PROGRAMME_S = 20.0


class AttestMixin:

    def _programme(self) -> bool:
        return self.music.playing or time.time() - self.bed_seen < PROGRAMME_S

    def _attest(self, audio: np.ndarray) -> dict:
        return self.voiceprints.attest(self.voiceprints.embed(audio), len(audio) / RATE, self._programme())

    def _identify_live(self, audio: np.ndarray) -> tuple:
        proof = self._attest(audio)
        return proof["slug"], proof["score"], self._known(proof["slug"])
