import asyncio
import json
import logging
import os
import shutil
import urllib.error
import urllib.request
from typing import Any

try:
    import earconf
except ImportError:
    from features.ear import earconf

try:
    from broadcast import SESSIONS
except ImportError:
    from features.ear.broadcast import SESSIONS

log = logging.getLogger("nuxiva.ear.host_mic")
SAMPLE_RATE = 16000
CHUNK_BYTES = 960
ASSISTANT_URL = os.environ.get("NUXIVA_ASSISTANT_URL", "http://127.0.0.1:8080/api/assistant/chat")
TTS_URL = os.environ.get("NUXIVA_TTS_URL", "http://127.0.0.1:8080/api/voice/speak")


class HeadlessSocket:

    def __init__(self) -> None:
        self.closed = False
        self.sent_events: list[dict] = []

    async def send(self, data: str) -> None:
        try:
            parsed = json.loads(data)
            self.sent_events.append(parsed)
            if parsed.get("type") == "transcript" and parsed.get("text"):
                asyncio.create_task(dispatch_headless_command(parsed))
        except (ValueError, TypeError):
            pass

    async def close(self, code: int = 1000, reason: str = "") -> None:
        self.closed = True


async def dispatch_headless_command(event: dict) -> None:
    text = str(event.get("text") or "").strip()
    if not text:
        return
    lang = str(event.get("lang") or "it")
    speaker = str(event.get("speaker") or "")
    payload = json.dumps({"text": text, "lang": lang, "speaker": speaker, "client_id": "headless_host_mic"}).encode("utf-8")
    req = urllib.request.Request(
        ASSISTANT_URL,
        data=payload,
        headers={"Content-Type": "application/json", "X-Nuxiva-Client": "headless_host_mic"}
    )
    loop = asyncio.get_running_loop()
    try:
        def _call_assistant() -> dict:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))

        data = await loop.run_in_executor(None, _call_assistant)
        reply = str(data.get("reply") or "").strip()
        if reply:
            await speak_reply(reply, lang)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        log.warning("Invio comando assistente headless non riuscito: %s", exc)


async def speak_reply(text: str, lang: str) -> None:
    payload = json.dumps({"text": text, "lang": lang}).encode("utf-8")
    req = urllib.request.Request(TTS_URL, data=payload, headers={"Content-Type": "application/json"})
    loop = asyncio.get_running_loop()
    try:
        def _call_tts() -> None:
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp.read()

        await loop.run_in_executor(None, _call_tts)
    except (urllib.error.URLError, TimeoutError, OSError):
        pass


def pick_capture_binary() -> list[str] | None:
    if os.environ.get("NUXIVA_MIC_CMD"):
        return os.environ["NUXIVA_MIC_CMD"].split()
    if shutil.which("parec"):
        return ["parec", "--rate=16000", "--channels=1", "--format=s16le"]
    if shutil.which("pw-record"):
        return ["pw-record", "--rate=16000", "--channels=1", "--format=s16"]
    if shutil.which("arecord"):
        return ["arecord", "-q", "-r", "16000", "-c", "1", "-f", "S16_LE", "-t", "raw"]
    return None


class HostMicCapture:

    def __init__(self, session_factory: Any) -> None:
        self.session_factory = session_factory
        self.session: Any = None
        self.running = False
        self.process: asyncio.subprocess.Process | None = None

    def should_capture(self) -> bool:
        if not earconf.flag("NUXIVA_EAR_HOST_MIC", True):
            return False
        for s in list(SESSIONS):
            if s is not self.session and getattr(s, "page", {}).get("visible") == "visible":
                return False
        return True

    async def run(self) -> None:
        self.running = True
        cmd = pick_capture_binary()
        if not cmd:
            log.info("Nessun comando di acquisizione nativo (parec/pw-record/arecord) rilevato per host mic")
            return
        while self.running:
            if not self.should_capture():
                await self._stop_process()
                await asyncio.sleep(2)
                continue
            if self.session is None:
                self.session = self.session_factory(HeadlessSocket())
                self.session.page = {"id": "host_mic", "visible": "headless"}
            try:
                self.process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL
                )
                assert self.process.stdout is not None
                while self.running and self.should_capture():
                    chunk = await self.process.stdout.read(CHUNK_BYTES)
                    if not chunk:
                        break
                    await self.session.feed(chunk)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                log.warning("Acquisizione audio host interrotta: %s", exc)
            finally:
                await self._stop_process()
            await asyncio.sleep(3)

    async def _stop_process(self) -> None:
        if self.process:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), 1.0)
            except (ProcessLookupError, TimeoutError, Exception):
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None

    async def stop(self) -> None:
        self.running = False
        await self._stop_process()
