import asyncio
import time

from agenti.collaudo import emit, hub, probes

ACTIVE = ("services", "bus_roundtrip", "camera_frame", "microphone_level", "ear_roundtrip", "sentinel_chain",
          "mcp_discovery", "sandbox_exec", "parity")
SCENARIOS = {"radio_rejected": "programme", "music_rejected": "programme", "owner_voice_accepted": "owner"}
PROBE_TIMEOUT = 330.0


async def _guard(name: str, corr: str, coroutine) -> dict:
    try:
        return await asyncio.wait_for(coroutine, PROBE_TIMEOUT)
    except asyncio.TimeoutError:
        return probes._result(name, "fail", corr, reason="timeout")
    except Exception as exc:
        emit.emit("error", "error", "probe_crashed", src="collaudo", corr=corr, probe=name, exc=type(exc).__name__.lower(), msg=str(exc)[:160])
        return probes._result(name, "fail", corr, reason="crashed")


async def run(only: list[str] | None = None) -> dict:
    corr = emit.new_corr()
    started = int(time.time() * 1000)
    previous = hub.get().collaudo()
    hub.get().set_collaudo(True)
    emit.emit("system", "info", "smoke_started", src="collaudo", corr=corr)
    results = []
    try:
        for name in ACTIVE:
            if only and name not in only:
                continue
            action = probes.microphone_level(corr, started) if name == "microphone_level" else getattr(probes, name)(corr)
            results.append(await _guard(name, corr, action))
        if not only or "collaudo_chain" in only:
            results.append(await _guard("collaudo_chain", corr, probes.collaudo_chain(corr)))
    finally:
        hub.get().set_collaudo(previous)
    emit.emit("system", "info", "smoke_finished", src="collaudo", corr=corr, probes=len(results))
    await asyncio.sleep(0.05)
    report = hub.report({"from_ms": started})
    return {"corr": corr, "started_ms": started, "results": results, "report": report}


async def scenario(name: str, seconds: float) -> dict:
    if name not in SCENARIOS:
        raise ValueError("collaudo.scenario.unknown")
    seconds = max(3.0, min(120.0, seconds))
    corr = emit.new_corr()
    started = int(time.time() * 1000)
    previous = hub.get().collaudo()
    hub.get().set_collaudo(True)
    try:
        await asyncio.sleep(seconds)
    finally:
        hub.get().set_collaudo(previous)
    events = await asyncio.to_thread(hub.query, {"domain": "ear", "from_ms": started, "limit": 5000})
    programme = sum(1 for e in events if e["kind"] == "level" and e["fields"].get("programme") is True)
    accepted = sum(1 for e in events if e["kind"] == "transcript" and e["fields"].get("programme") is True) if SCENARIOS[name] == "programme" \
        else sum(1 for e in events if e["kind"] == "transcript" and e["fields"].get("voice_known") is True)
    seconds_programme = round(programme * 0.25, 1)
    if SCENARIOS[name] == "programme" and seconds_programme < 1.0:
        return probes._result(name, "skip", corr, reason="no_programme_heard", programme_s=seconds_programme, accepted_n=accepted)
    outcome = "ok" if (accepted == 0 if SCENARIOS[name] == "programme" else accepted >= 1) else "fail"
    return probes._result(name, outcome, corr, programme_s=seconds_programme, accepted_n=accepted)
