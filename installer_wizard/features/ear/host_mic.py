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


def _get_broadcast_module():
    for mod_name in ("features.ear.broadcast", "broadcast", "installer_wizard.features.ear.broadcast"):
        if mod_name in sys.modules:
            mod = sys.modules[mod_name]
            if hasattr(mod, "SESSIONS"):
                return mod
    try:
        from features.ear import broadcast
        return broadcast
    except ImportError:
        try:
            import broadcast
            return broadcast
        except ImportError:
            from installer_wizard.features.ear import broadcast
            return broadcast


def _get_sessions() -> set:
    mod = _get_broadcast_module()
    return getattr(mod, "SESSIONS", set())


def _register_session(session: Any) -> None:
    mod = _get_broadcast_module()
    if hasattr(mod, "register"):
        mod.register(session)
    elif hasattr(mod, "SESSIONS"):
        mod.SESSIONS.add(session)


def _unregister_session(session: Any) -> None:
    mod = _get_broadcast_module()
    if hasattr(mod, "unregister"):
        mod.unregister(session)
    elif hasattr(mod, "SESSIONS"):
        mod.SESSIONS.discard(session)


log = logging.getLogger("nuxiva.ear.host_mic")
SAMPLE_RATE = 16000
CHUNK_BYTES = 960
PUBLIC_URL = "http://127.0.0.1:" + os.environ.get("NUXIVA_PUBLIC_PORT", "80")
ASSISTANT_URL = os.environ.get("NUXIVA_ASSISTANT_URL", PUBLIC_URL + "/api/assistant/chat")
TTS_URL = os.environ.get("NUXIVA_TTS_URL", PUBLIC_URL + "/api/voice/speak")
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


_ACTIVE_TASKS: set[asyncio.Task] = set()


def _spawn_background_task(coro) -> asyncio.Task:
    task = asyncio.create_task(coro)
    _ACTIVE_TASKS.add(task)
    task.add_done_callback(_ACTIVE_TASKS.discard)
    return task


class HeadlessSocket:

    def __init__(self) -> None:
        self.closed = False
        self._wake_announced = False

    async def send(self, data: str) -> None:
        if self.closed:
            return
        try:
            event = json.loads(data)
            if event.get("origin") is False:
                return
            if event.get("type") in ("wake", "wake_only"):
                if not self._wake_announced:
                    self._wake_announced = True
                    _spawn_background_task(play_wake_feedback())
            elif event.get("type") == "transcript" or (
                event.get("type") == "state" and event.get("state") == "idle"
            ):
                self._wake_announced = False
            if event.get("type") == "transcript" and event.get("text") and event.get("origin") is not False:
                _spawn_background_task(dispatch_headless_command(event))
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            log.debug("Evento headless non valido: %s", exc)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        self.closed = True


async def play_wake_feedback() -> None:
    if not earconf.flag("NUXIVA_EAR_HOST_WAKE_SOUND", True):
        return
    try:
        from features.voices.feedback import wake_wav
        from features.voices.playback import play_host_audio

        await play_host_audio(wake_wav())
    except Exception:
        log.warning("Feedback sonoro di attivazione host non disponibile", exc_info=True)


async def dispatch_headless_command(event: dict) -> None:
    text = str(event.get("text") or "").strip()
    if not text:
        return
    lang = str(event.get("lang") or "it")
    speaker = str(event.get("speaker") or "")
    log.info("Inoltro comando vocale headless all'assistente: '%s' (lang=%s, speaker=%s)", text, lang, speaker or "sconosciuto")
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
            log.info("Risposta assistente headless ricevuta: '%s' (%d caratteri)", reply[:60], len(reply))
            await speak_reply(reply, lang)
        else:
            log.info("Nessuna risposta testuale da sintetizzare per il comando headless")
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
        if res.get("ok"):
            log.info("Sintesi vocale TTS riprodotta con successo: %s (ok=%s)", text[:60], res.get("ok"))
        else:
            log.warning("Riproduzione sintesi vocale TTS headless non riuscita: %s", text[:60])
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        log.warning("Invio sintesi vocale TTS headless a %s non riuscito: %s", TTS_URL, exc)


class HostMicCapture:

    def __init__(self, session_factory: Any) -> None:
        self.session_factory = session_factory
        self.session: Any = None
        self.running = False
        self.process: asyncio.subprocess.Process | None = None
        self._stderr_task: asyncio.Task | None = None
        self._stderr_tail = b""

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

    def _teardown_session(self) -> None:
        if self.session is not None:
            _unregister_session(self.session)
            if hasattr(self.session, "ws"):
                self.session.ws.closed = True
            self.session = None
            log.debug("Sessione host mic headless deregistrata da SESSIONS")

    async def run(self) -> None:
        self.running = True
        candidates = get_capture_candidates()
        if not candidates:
            log.info("Nessun comando di acquisizione nativo (parec/pw-record/arecord) rilevato per host mic")
            return
        candidate_idx = 0
        try:
            while self.running:
                if not self.should_capture():
                    await self._stop_process()
                    if not earconf.flag("NUXIVA_EAR_HOST_MIC", True):
                        self._teardown_session()
                    await asyncio.sleep(1)
                    continue
                if self.session is None:
                    self.session = self.session_factory(HeadlessSocket())
                    self.session.page = {"id": "host_mic", "page": "host_mic", "visible": "headless"}
                    _register_session(self.session)
                    log.info("Sessione host mic headless inizializzata e registrata in SESSIONS")
                cmd = candidates[candidate_idx % len(candidates)]
                read_any = False
                start_time = time.time()
                try:
                    self.process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    self._stderr_tail = b""
                    if self.process.stderr is not None:
                        self._stderr_task = asyncio.create_task(self._drain_stderr(self.process.stderr))
                    assert self.process.stdout is not None
                    pending = b""
                    while self.running and self.should_capture():
                        chunk = await self.process.stdout.read(CHUNK_BYTES)
                        if not chunk:
                            break
                        read_any = True
                        chunk = pending + chunk
                        boundary = len(chunk) - len(chunk) % 2
                        pending = chunk[boundary:]
                        if boundary:
                            await self.session.feed(chunk[:boundary])
                        await asyncio.sleep(0)
                except asyncio.CancelledError:
                    raise
                except (OSError, RuntimeError, ValueError) as exc:
                    log.warning("Errore cattura host mic (%s): %s", cmd[0], exc)
                finally:
                    await self._stop_process()
                elapsed = time.time() - start_time
                if not read_any or elapsed < 1.5:
                    candidate_idx += 1
                    if len(candidates) > 1:
                        next_cmd = candidates[candidate_idx % len(candidates)]
                        log.info("Rotazione comando cattura microfono host: fallback da %s a %s", cmd[0], next_cmd[0])
                await asyncio.sleep(1)
        finally:
            await self._stop_process()
            self._teardown_session()

    async def _drain_stderr(self, stream) -> None:
        try:
            while chunk := await stream.read(1024):
                self._stderr_tail = (self._stderr_tail + chunk)[-2048:]
        except OSError as exc:
            log.warning("Lettura diagnostica cattura host non riuscita: %s", exc)

    async def _stop_process(self) -> None:
        if self.process is not None:
            process, self.process = self.process, None
            try:
                process.terminate()
            except ProcessLookupError:
                log.debug("Processo cattura già terminato")
            try:
                await asyncio.wait_for(process.wait(), timeout=1.0)
            except asyncio.TimeoutError:
                try:
                    process.kill()
                except ProcessLookupError:
                    log.debug("Processo cattura già terminato prima del kill")
                await process.wait()
        if self._stderr_task is not None:
            self._stderr_task.cancel()
            results = await asyncio.gather(self._stderr_task, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    log.error("Errore task diagnostica cattura host: %s", result)
            self._stderr_task = None
        if self._stderr_tail:
            log.debug("Diagnostica cattura host: %s", self._stderr_tail.decode("utf-8", "replace").strip())

    def stop(self) -> None:
        self.running = False
        if self.process is not None:
            try:
                self.process.terminate()
            except ProcessLookupError:
                log.debug("Processo cattura già terminato durante stop")
        self._teardown_session()
