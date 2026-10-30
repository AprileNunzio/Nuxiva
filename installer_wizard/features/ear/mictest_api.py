import asyncio
import base64
import logging
import time
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ConfigDict, Field

import auth
from access import require_admin
from config import env_get
from features.authz.access_control import require_permission
from features.ear import equalizer, mictest
from features.ear.micsource import MicBusy, MicSource, MicUnavailable
from features.ear.tuning import tuning
from state import store

log = logging.getLogger("nuxiva.ear.mictest")
routes = APIRouter()
POLICY_VIOLATION = 1008
METER_INTERVAL_S = 0.05
METER_MAX_S = 120.0
METER_BYTES = mictest.METER_FRAME * 2
TARGET_MIN, TARGET_MAX = 0.03, 0.2


class EqDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    highpass_hz: float = Field(ge=equalizer.HIGHPASS_MIN, le=equalizer.HIGHPASS_MAX, allow_inf_nan=False)
    low_db: float = Field(ge=equalizer.GAIN_DB_MIN, le=equalizer.GAIN_DB_MAX, allow_inf_nan=False)
    mid_db: float = Field(ge=equalizer.GAIN_DB_MIN, le=equalizer.GAIN_DB_MAX, allow_inf_nan=False)
    high_db: float = Field(ge=equalizer.GAIN_DB_MIN, le=equalizer.GAIN_DB_MAX, allow_inf_nan=False)


class MicTestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seconds: float = Field(default=5.0, ge=1.0, le=10.0, allow_inf_nan=False)
    target_rms: float | None = Field(default=None, ge=TARGET_MIN, le=TARGET_MAX, allow_inf_nan=False)
    eq: EqDraft | None = None


def saved_target() -> float:
    try:
        value = float(env_get("NUXIVA_EAR_TARGET_RMS", "0.075"))
    except ValueError:
        return 0.075
    return min(TARGET_MAX, max(TARGET_MIN, value))


def chain_for(body: MicTestRequest) -> mictest.Chain:
    tuning.load()
    saved = equalizer.EqSettings.from_source(env_get)
    eq = equalizer.EqSettings.from_mapping(body.eq.model_dump(), saved) if body.eq else saved
    autotuned = bool(tuning.snapshot()["autotune"]) and (tuning.state.get("max_gain") is not None
                                                         or float(tuning.state.get("wake_gain") or 1.0) != 1.0)
    return mictest.Chain(eq=eq, target_rms=body.target_rms or saved_target(), max_gain=tuning.max_gain(),
                         wake_gain_limit=tuning.wake_gain_limit(), autotuned=autotuned)


def capture_error(exc: Exception) -> HTTPException:
    if isinstance(exc, MicBusy):
        return HTTPException(409, "mic_busy")
    return HTTPException(503, str(exc) or "mic_unavailable")


@routes.post("/api/ear/mictest")
async def run_mictest(body: MicTestRequest, user: str = Depends(require_admin)):
    chain = chain_for(body)
    try:
        async with MicSource() as source:
            pcm = await source.record(body.seconds)
    except (MicBusy, MicUnavailable) as exc:
        raise capture_error(exc) from exc
    report, raw, processed = await asyncio.to_thread(mictest.analyze, pcm, chain)
    store.event("INFO", f"Test del microfono di {body.seconds:.0f} s eseguito da {user}: {report['verdict']}", "ear")
    return {"report": report, "audio": {"mime": "audio/wav", "raw": base64.b64encode(raw).decode("ascii"),
                                        "processed": base64.b64encode(processed).decode("ascii")}}


def socket_user(socket: WebSocket) -> str | None:
    origin = socket.headers.get("origin", "")
    host = socket.headers.get("host", "")
    if not origin or not host or urlsplit(origin).netloc.lower() != host.lower():
        return None
    user = auth.verify(socket.cookies.get(auth.SESSION_COOKIE))
    if not user or user == "display":
        return None
    try:
        require_permission(user, "api.admin")
    except HTTPException:
        return None
    return user


async def stream_levels(socket: WebSocket, source: MicSource) -> None:
    deadline = time.monotonic() + METER_MAX_S
    last = 0.0
    while time.monotonic() < deadline:
        block = mictest.to_samples(await source.read(METER_BYTES))
        now = time.monotonic()
        if now - last >= METER_INTERVAL_S:
            last = now
            await socket.send_json({"type": "level", **mictest.meter(block)})
    await socket.send_json({"type": "timeout"})


async def wait_disconnect(socket: WebSocket) -> None:
    while (await socket.receive())["type"] != "websocket.disconnect":
        continue


@routes.websocket("/api/ear/mictest/meter")
async def meter_socket(socket: WebSocket):
    if socket_user(socket) is None:
        await socket.close(code=POLICY_VIOLATION)
        return
    await socket.accept()
    try:
        async with MicSource() as source:
            await socket.send_json({"type": "ready"})
            tasks = [asyncio.create_task(stream_levels(socket, source)), asyncio.create_task(wait_disconnect(socket))]
            try:
                done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            finally:
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
            for task in done:
                if not task.cancelled() and task.exception() is not None:
                    raise task.exception()
    except (MicBusy, MicUnavailable) as exc:
        await socket.send_json({"type": "error", "code": "mic_busy" if isinstance(exc, MicBusy) else str(exc)})
    except (WebSocketDisconnect, RuntimeError) as exc:
        log.debug("Meter del microfono chiuso: %s", exc)
        return
    try:
        await socket.close()
    except RuntimeError:
        return
