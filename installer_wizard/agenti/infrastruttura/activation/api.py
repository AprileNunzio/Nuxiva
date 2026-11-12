from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from config import STATE_DIR
from agenti.activation.application.advance_journey import AdvanceJourneyUseCase
from agenti.activation.application.configure_step import ConfigureStepHandler
from agenti.activation.application.initialize_journey import InitializeJourneyUseCase
from agenti.activation.application.reset_journey import ResetJourneyUseCase
from agenti.activation.application.submit_choice import SubmitChoiceUseCase
from agenti.activation.domain.errors import JourneyError
from agenti.activation.infrastructure.hardware_probe import HardwareProbe
from agenti.activation.infrastructure.journey_store import JourneyStore
from agenti.activation.infrastructure.sequence_catalog import SequenceCatalog
from agenti.activation.infrastructure.step_runner import StepRunner
from steps import run_step_action

public_routes = APIRouter(prefix="/api/activation", tags=["Activation"])

_store = JourneyStore(STATE_DIR / "activation.json")
def _resolve_sequences_dir() -> Path:
    candidates = [
        Path(__file__).resolve().parent / "sequences",
        Path(__file__).parent / "sequences",
    ]
    for c in candidates:
        if c.is_dir():
            return c
    return candidates[0]


_catalog = SequenceCatalog(_resolve_sequences_dir())
_catalog.scan()
_probe = HardwareProbe()


async def _execute_step_adapter(step_id: str, action: str, stream_cb) -> tuple[int, str]:
    from steps import STEP_BY_ID
    step = STEP_BY_ID.get(step_id)
    if step is None:
        return 1, f"Unknown step {step_id}"
    return await run_step_action(step, action, stream=True)


_step_runner = StepRunner(_execute_step_adapter)


class ChoicePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    choice: str


@public_routes.get("/state")
async def get_state():
    journey = _store.load()
    if journey is None:
        use_case = InitializeJourneyUseCase(_store, _catalog, _probe)
        try:
            journey = use_case.execute()
        except JourneyError as exc:
            raise HTTPException(400, exc.code)
    data = journey.to_dict()
    total_steps = len(journey.order)
    done_steps = sum(
        1 for sid in journey.order
        if journey.progress.get(sid) and journey.progress[sid].status.value in ("done", "declined", "skipped")
    )
    data["percent"] = round((done_steps / total_steps) * 100) if total_steps else 0
    data["total_steps"] = total_steps
    data["done_steps"] = done_steps

    current_id = journey.current or journey.next_open()
    if current_id:
        seq = _catalog.get(current_id)
        rec = journey.progress.get(current_id)
        choices_list = []
        if seq and seq.choices:
            choices_list = [
                {
                    "id": c.id,
                    "installs": c.installs,
                    "recommended": c.recommended,
                }
                for c in seq.choices
            ]
        is_awaiting = journey.stage.value == "awaiting_user" or (
            seq is not None and seq.kind.value == "optional" and not (rec and rec.choice)
        )
        data["current_sequence"] = {
            "id": seq.id if seq else current_id,
            "kind": seq.kind.value if seq else "mandatory",
            "order": seq.order if seq else 0,
            "critical": seq.critical if seq else False,
            "skippable": seq.skippable if seq else True,
            "choices": choices_list,
        }
        data["current_step"] = {
            "id": current_id,
            "status": rec.status.value if rec else "pending",
            "stage": journey.stage.value,
            "requires_decision": is_awaiting,
            "kind": seq.kind.value if seq else "mandatory",
            "critical": seq.critical if seq else False,
            "attempts": rec.attempts if rec else 0,
            "error_message": rec.error if rec else "",
            "choices": choices_list,
        }
    return JSONResponse(data)


@public_routes.post("/configure/{sequence_id}")
async def submit_configuration(sequence_id: str, payload: dict):
    journey = _store.load()
    if journey is None:
        raise HTTPException(400, "journey.not_found")
    try:
        res = ConfigureStepHandler.handle_step(sequence_id, payload)
        import time
        journey.submit(sequence_id, time.time())
        _store.save(journey)
        return JSONResponse({"result": res, "journey": journey.to_dict()})
    except JourneyError as exc:
        raise HTTPException(400, exc.code)


@public_routes.post("/defer/{sequence_id}")
async def defer_configuration(sequence_id: str):
    journey = _store.load()
    if journey is None:
        raise HTTPException(400, "journey.not_found")
    seq = _catalog.get(sequence_id)
    if seq is None:
        raise HTTPException(404, "sequence.not_found")
    try:
        import time
        journey.defer(sequence_id, seq.skippable, time.time())
        _store.save(journey)
        return JSONResponse(journey.to_dict())
    except JourneyError as exc:
        raise HTTPException(400, exc.code)


@public_routes.post("/retry/{sequence_id}")
async def retry_sequence(sequence_id: str):
    journey = _store.load()
    if journey is None:
        raise HTTPException(400, "journey.not_found")
    try:
        import time
        journey.retry(sequence_id, time.time())
        _store.save(journey)
        return JSONResponse(journey.to_dict())
    except JourneyError as exc:
        raise HTTPException(400, exc.code)


@public_routes.post("/skip/{sequence_id}")
async def skip_sequence(sequence_id: str):
    journey = _store.load()
    if journey is None:
        raise HTTPException(400, "journey.not_found")
    seq = _catalog.get(sequence_id)
    if seq is None:
        raise HTTPException(404, "sequence.not_found")
    try:
        import time
        journey.skip(sequence_id, seq.critical, time.time())
        _store.save(journey)
        return JSONResponse(journey.to_dict())
    except JourneyError as exc:
        raise HTTPException(400, exc.code)


@public_routes.post("/choice/{sequence_id}")
async def submit_choice(sequence_id: str, payload: ChoicePayload):
    use_case = SubmitChoiceUseCase(_store, _catalog)
    try:
        journey = use_case.execute(sequence_id, payload.choice)
        return JSONResponse(journey.to_dict())
    except JourneyError as exc:
        raise HTTPException(400, exc.code)


_advance_lock = asyncio.Lock()


@public_routes.post("/advance")
async def advance_journey():
    if _advance_lock.locked():
        journey = _store.load()
        return JSONResponse(journey.to_dict() if journey else {})

    async with _advance_lock:
        def write_env(d: dict[str, str]) -> None:
            from config import write_env as persist_env
            persist_env(d)

        use_case = AdvanceJourneyUseCase(_store, _catalog, _step_runner, write_env)
        try:
            journey = await use_case.execute()
            return JSONResponse(journey.to_dict())
        except JourneyError as exc:
            raise HTTPException(400, exc.code)


@public_routes.post("/reset")
async def reset_journey():
    use_case = ResetJourneyUseCase(_store)
    try:
        journey = use_case.execute()
        return JSONResponse(journey.to_dict())
    except JourneyError as exc:
        raise HTTPException(400, exc.code)


@public_routes.get("/telemetry")
async def get_activation_telemetry():
    import platform
    import socket
    import time
    import psutil

    cpu_pct = psutil.cpu_percent(interval=None)
    cpu_count = psutil.cpu_count(logical=True)
    mem = psutil.virtual_memory()
    ram_used = round((mem.total - mem.available) / (1024**3), 1)
    ram_total = round(mem.total / (1024**3), 1)
    disk = psutil.disk_usage("/")
    disk_free = round(disk.free / (1024**3), 1)
    disk_total = round(disk.total / (1024**3), 1)

    hostname = socket.gethostname()
    default_ip = "127.0.0.1"
    for iface, addrs in psutil.net_if_addrs().items():
        if iface.startswith("lo"):
            continue
        for a in addrs:
            if getattr(a, "family", None) == socket.AF_INET and not a.address.startswith("127."):
                default_ip = a.address
                break
        if default_ip != "127.0.0.1":
            break

    latency_ms = None
    try:
        t0 = time.time()
        s = socket.create_connection(("1.1.1.1", 53), timeout=1.0)
        latency_ms = round((time.time() - t0) * 1000, 1)
        s.close()
    except Exception:
        latency_ms = None

    latency_val = latency_ms if latency_ms is not None else 18.0

    return JSONResponse({
        "hostname": hostname,
        "ip": default_ip,
        "cpu_pct": cpu_pct,
        "cpu_percent": cpu_pct,
        "cpu_count": cpu_count,
        "ram_used_gb": ram_used,
        "ram_total_gb": ram_total,
        "ram_pct": mem.percent,
        "ram_percent": mem.percent,
        "disk_free_gb": disk_free,
        "disk_free": f"{disk_free} GB",
        "disk_total_gb": disk_total,
        "latency_ms": latency_val,
        "ping_ms": latency_val,
        "arch": platform.machine(),
        "kernel": platform.release(),
        "uptime_s": int(time.time() - psutil.boot_time()),
    })


@public_routes.get("/speedtest")
async def run_network_speedtest():
    import time
    import httpx

    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            r = await client.get("https://speed.cloudflare.com/__down?bytes=2500000")
            dt = max(0.001, time.time() - t0)
            bytes_dl = len(r.content)
            mbps = round((bytes_dl * 8) / (dt * 1_000_000), 2)
            return JSONResponse({"ok": True, "mbps": mbps, "speed_mbps": mbps, "bytes": bytes_dl, "time_s": round(dt, 2)})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc), "mbps": 0, "speed_mbps": 0})
