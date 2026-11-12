import os
import logging
import tempfile
import threading
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

app = FastAPI()
MAX_AUDIO_BYTES = 32 * 1024 * 1024
_lock = threading.Lock()
_model = None


def transcribe_audio(audio: bytes) -> dict:
    global _model
    with _lock:
        if _model is None:
            from faster_whisper import WhisperModel

            _model = WhisperModel(os.environ.get("NUXIVA_WHISPER_MODEL", "small"), device="cuda", compute_type="float16")
        with tempfile.NamedTemporaryFile(suffix=".audio", delete=False) as handle:
            path = Path(handle.name)
            handle.write(audio)
        try:
            segments, info = _model.transcribe(str(path), vad_filter=True)
            return {"text": " ".join(segment.text.strip() for segment in segments).strip(),
                    "language": info.language, "language_probability": info.language_probability}
        finally:
            path.unlink(missing_ok=True)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model_loaded": _model is not None}


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)) -> dict:
    try:
        audio = await file.read(MAX_AUDIO_BYTES + 1)
    finally:
        await file.close()
    if not audio:
        raise HTTPException(400, "File audio vuoto")
    if len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(413, "File audio troppo grande")
    try:
        return await run_in_threadpool(transcribe_audio, audio)
    except ValueError as exc:
        raise HTTPException(400, "File audio non valido") from exc
    except Exception as exc:
        logging.getLogger("nuxiva.inference").exception("GPU transcription failed")
        raise HTTPException(503, "Servizio di trascrizione GPU non disponibile") from exc
