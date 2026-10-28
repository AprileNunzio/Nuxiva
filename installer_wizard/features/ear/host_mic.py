import asyncio
import json
import logging
import os
import shutil
import sys
import time
import urllib.error
import urllib.request
from typing import Any

try:
    from features.ear import earconf
except ImportError:
    try:
        import earconf
    except ImportError:
        from installer_wizard.features.ear import earconf


def _get_sessions() -> set:
    for mod_name in ("features.ear.broadcast", "broadcast", "installer_wizard.features.ear.broadcast"):
        if mod_name in sys.modules:
            mod = sys.modules[mod_name]
            if hasattr(mod, "SESSIONS"):
                return mod.SESSIONS
    try:
        from features.ear.broadcast import SESSIONS
        return SESSIONS
    except ImportError:
        try:
            from broadcast import SESSIONS
            return SESSIONS
        except ImportError:
            from installer_wizard.features.ear.broadcast import SESSIONS
            return SESSIONS


log = logging.getLogger("nuxiva.ear.host_mic")
SAMPLE_RATE = 16000
CHUNK_BYTES = 960
ASSISTANT_URL = os.environ.get("NUXIVA_ASSISTANT_URL", "http://127.0.0.1:8080/api/assistant/chat")
TTS_URL = os.environ.get("NUXIVA_TTS_URL", "http://127.0.0.1:8080/api/voice/speak")
KIOSK_USER = os.environ.get("NUXIVA_KIOSK_USER", "nuxiva-kiosk")


def _get_kiosk_uid() -> int | None:
    try:
        import pwd
        return pwd.getpwnam(KIOSK_USER).pw_uid
    except (KeyError, ImportError):
        return None


def get_capture_candidates() -> list[list[str]]:
    custom = os.environ.get("NUXIVA_MIC_CMD")
    if custom:
        return [custom.split()]
    cmds: list[list[str]] = []
    uid = _get_kiosk_uid()
    if shutil.which("parec"):
        if os.name != "nt" and hasattr(os, "getuid") and os.getuid() == 0 and uid is not None and shutil.which("runuser"):
            cmds.append(["runuser", "-u", KIOSK_USER, "--", "env", f"XDG_RUNTIME_DIR=/run/user/{uid}", "parec", "--rate=16000", "--channels=1", "--format=s16le"])
        cmds.append(["parec", "--rate=16000", "--channels=1", "--format=s16le"])
    if shutil.which("pw-record"):
        cmds.append(["pw-record", "--rate=16000", "--channels=1", "--format=s16"])
    if shutil.which("arecord"):
        cmds.append(["arecord", "-q", "-r", "16000", "-c", "1", "-f", "S16_LE", "-t", "raw"])
    return cmds


def pick_capture_binary() -> list[str] | None:
    candidates = get_capture_candidates()
    return candidates[0] if candidates else None


class HeadlessSocket:

    def __init__(self) -> None:
        self.closed = False

    async def send(self, data: str) -> None:
        if self.closed:
            return
        try:
            event = json.loads(data)
            if event.get("type") == "transcript" and event.get("text"):
                asyncio.create_task(dispatch_headless_command(event))
        except (json.JSONDecodeError, TypeError, ValueError):
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
    text = (text or "").strip()
    if not text:
        return
    payload = json.dumps({"text": text, "lang": lang}).encode("utf-8")
    req = urllib.request.Request(
        TTS_URL,
        data=payload,
        headers={"Content-Type": "application/json", "X-Nuxiva-Client": "headless_host_mic"}
    )
    loop = asyncio.get_running_loop()
    try:
        def _call_tts() -> dict:
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read().decode("utf-8", "replace")
                return json.loads(raw) if raw.startswith("{") else {"ok": True}

        res = await loop.run_in_executor(None, _call_tts)
        log.info("Sintesi vocale TTS riprodotta con successo: %s (ok=%s)", text[:60], res.get("ok"))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        log.warning("Invio sintesi vocale TTS headless a %s non riuscito: %s", TTS_URL, exc)


class HostMicCapture:

    def __init__(self, session_factory: Any) -> None:
        self.session_factory = session_factory
        self.session: Any = None
        self.running = False
        self.process: asyncio.subprocess.Process | None = None

    def should_capture(self) -> bool:
        if not earconf.flag("NUXIVA_EAR_HOST_MIC", True):
            return False
        now = time.time()
        for s in list(_get_sessions()):
            if s is not self.session and getattr(s, "last_pcm_time", 0.0) > (now - 2.5):
                return False
        return True

    def is_capturing(self) -> bool:
        return self.running and self.process is not None and self.should_capture()

    async def run(self) -> None:
        self.running = True
        candidates = get_capture_candidates()
        if not candidates:
            log.info("Nessun comando di acquisizione nativo (parec/pw-record/arecord) rilevato per host mic")
            return
        candidate_idx = 0
        while self.running:
            if not self.should_capture():
                await self._stop_process()
                await asyncio.sleep(1)
                continue
            if self.session is None:
                self.session = self.session_factory(HeadlessSocket())
                self.session.page = {"id": "host_mic", "visible": "headless"}
            cmd = candidates[candidate_idx % len(candidates)]
            read_any = False
            start_time = time.time()
            try:
                self.process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                assert self.process.stdout is not None
                while self.running and self.should_capture():
                    chunk = await self.process.stdout.read(CHUNK_BYTES)
                    if not chunk:
                        break
                    read_any = True
                    await self.session.feed(chunk)
            except (asyncio.CancelledError, Exception) as exc:
                log.debug("Errore o interruzione processo cattura host mic (%s): %s", cmd[0], exc)
            finally:
                await self._stop_process()
            elapsed = time.time() - start_time
            if not read_any or elapsed < 1.5:
                candidate_idx += 1
                if len(candidates) > 1:
                    next_cmd = candidates[candidate_idx % len(candidates)]
                    log.info("Rotazione comando cattura microfono host: fallback da %s a %s", cmd[0], next_cmd[0])
            await asyncio.sleep(1)

    async def _stop_process(self) -> None:
        if self.process is not None:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=1.0)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            finally:
                self.process = None

    def stop(self) -> None:
        self.running = False
        if self.process is not None:
            try:
                self.process.terminate()
            except Exception:
                pass
