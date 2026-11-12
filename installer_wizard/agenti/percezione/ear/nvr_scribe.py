import asyncio
import logging
import math

import numpy as np

import scribe_spool

log = logging.getLogger("nuxiva.ear.nvr")
RATE = 16000
IDLE_S = 10.0
CLUSTER_AT = 0.72
MAX_SECONDS = 600
UNKNOWN = "voce"


def py_cluster(embeddings: list[list[float]], threshold: float) -> list[int]:
    centroids: list[list] = []
    labels = []
    for e in embeddings:
        if any(not math.isfinite(x) for x in e):
            raise ValueError("nvr.voices.invalid")
        best, best_score = None, None
        for i, (c, _) in enumerate(centroids):
            denom = math.sqrt(sum(x * x for x in e)) * math.sqrt(sum(x * x for x in c))
            score = sum(a * b for a, b in zip(e, c)) / denom if denom > 1.1920929e-07 and len(e) == len(c) else -1.0
            if score >= threshold and (best_score is None or score > best_score):
                best, best_score = i, score
        if best is None:
            labels.append(len(centroids))
            centroids.append([list(map(float, e)), 1.0])
        else:
            c, n = centroids[best]
            centroids[best] = [[(ci * n + ei) / (n + 1.0) for ci, ei in zip(c, e)], n + 1.0]
            labels.append(best)
    return labels


def cluster(embeddings: list[list[float]], threshold: float = CLUSTER_AT) -> list[int]:
    try:
        import nuxiva_native
        return list(nuxiva_native.nvr_cluster_voices(embeddings, threshold))
    except (ImportError, AttributeError):
        return py_cluster(embeddings, threshold)


def label_speakers(segments: list[dict], audio: np.ndarray, voiceprints) -> list[dict]:
    unknown_idx, unknown_emb = [], []
    out = []
    for seg in segments:
        piece = audio[int(seg["start"] * RATE):int(seg["end"] * RATE)]
        probe = voiceprints.embed(piece) if voiceprints is not None and getattr(voiceprints, "ready", False) else None
        slug, score = voiceprints.identify(probe) if probe is not None else (None, 0.0)
        row = {"start_ms": int(seg["start"] * 1000), "end_ms": int(seg["end"] * 1000), "text": str(seg["text"])[:4000],
               "speaker": slug, "speaker_score": round(float(score or 0.0), 4)}
        if slug is None and probe is not None:
            unknown_idx.append(len(out))
            unknown_emb.append(np.asarray(probe, dtype=np.float32).tolist())
        out.append(row)
    if unknown_emb:
        for index, label in zip(unknown_idx, cluster(unknown_emb)):
            out[index]["voice"] = f"{UNKNOWN}-{label + 1}"
    return out


class NvrScribe:
    def __init__(self, voiceprints, busy, transcribe=None) -> None:
        self.voiceprints = voiceprints
        self.busy = busy
        self.transcribe = transcribe

    def _segments(self, audio: np.ndarray) -> list[dict]:
        if self.transcribe is not None:
            return self.transcribe(audio)
        import stt
        return stt.transcribe_segments(audio)

    def process(self, name: str) -> bool:
        header, pcm = scribe_spool.take("jobs", name)
        audio = np.frombuffer(pcm[:RATE * 2 * MAX_SECONDS], dtype="<i2").astype(np.float32) / 32768.0
        segments = self._segments(audio) if len(audio) >= RATE // 2 else []
        turns = label_speakers(segments, audio, self.voiceprints)
        scribe_spool.put("done", name, {"camera": header.get("camera"), "segment": header.get("segment"),
                                        "start_ms": header.get("start_ms"), "turns": turns,
                                        "seconds": round(len(audio) / RATE, 2)})
        return True

    async def run(self) -> None:
        while True:
            await asyncio.sleep(IDLE_S)
            if self.busy():
                continue
            for name in scribe_spool.names("jobs")[:4]:
                if self.busy():
                    break
                try:
                    import stt
                    async with stt.lock:
                        await asyncio.to_thread(self.process, name)
                except (scribe_spool.SpoolError, ValueError, OSError) as exc:
                    log.warning("Trascrizione registrazione %s scartata: %s", name, exc)
