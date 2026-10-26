import asyncio
import json
import os
import sys
from pathlib import Path

DEMO: bool = False

import packages
from config import NUXIVA_DIR
from features.selftest.skip import Skip
from sandbox_broker.config import BrokerConfig
from state import store


async def sandbox_isolation():
    if os.name == "nt":
        raise Skip("la sandbox gira solo sul server")
    status = (store.steps.get("sandbox") or {}).get("status")
    if status == "on_demand" and not packages.step_wanted("sandbox") and not Path(BrokerConfig.from_env().socket_path).exists():
        raise Skip("sandbox non installata, disponibile su richiesta; isolamento non verificato")
    env = {**os.environ, "PYTHONPATH": str(NUXIVA_DIR)}
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "sandbox_broker.selfcheck", cwd=str(NUXIVA_DIR), env=env,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        out, err = await asyncio.wait_for(proc.communicate(), 90)
    except asyncio.TimeoutError:
        proc.kill()
        raise AssertionError("la sandbox non ha risposto entro 90 secondi")
    try:
        outcome = json.loads(out.decode("utf-8", "replace").strip().splitlines()[-1])
    except (ValueError, IndexError):
        raise AssertionError(f"risposta illeggibile: {err.decode('utf-8', 'replace')[-160:] or sys.executable}")
    if not outcome["ok"]:
        raise AssertionError("; ".join(outcome["problems"]))
    return (f"codice eseguito in isolamento ({outcome['backend']}): niente rete, disco di sola lettura, utente non root"
            f" | backend: {_backends(outcome.get('backends') or [])}")


def _backends(items):
    return ", ".join(f"{b['name']}={'ok' if b['available'] else 'no'}{' (' + b['note'] + ')' if b.get('note') else ''}" for b in items)[:600]

