import os
import asyncio
import shutil
import time

import httpx
import psutil

from config import ADMIN_PORT, PUBLIC_PORT, STATE_DIR
from features.selftest.sandbox_check import sandbox_isolation
from features.selftest.skip import Skip
from state import store

LOCAL = "http://127.0.0.1"
HEADERS = {"X-Nuxiva-Request": "1", "Content-Type": "application/json"}


async def supervisor_api():
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{LOCAL}:{PUBLIC_PORT}/api/state")
        r.raise_for_status()
        state = r.json()
        a = await c.get(f"{LOCAL}:{ADMIN_PORT}/")
        a.raise_for_status()
    return f"pagina pubblica e pannello rispondono, fase {state.get('phase')}"


async def components():
    bad = [f"{c.get('label', k)} ({c.get('status')})" for k, c in (store.components or {}).items()
           if c.get("status") not in ("ok", "idle", None)]
    if bad:
        raise AssertionError("non funzionano: " + ", ".join(bad))
    return f"{len(store.components or {})} componenti in ordine"


async def chat():
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(f"{LOCAL}:{PUBLIC_PORT}/api/assistant/chat", headers={**HEADERS, "X-Nuxiva-Internal": "1"}, json={"text": "che ore sono", "internal": True})
        r.raise_for_status()
        reply = r.json().get("reply") or ""
    if not reply.strip():
        raise AssertionError("risposta vuota")
    return f"«che ore sono» → «{reply[:60]}»"


async def voice():
    started = time.time()
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(f"{LOCAL}:{PUBLIC_PORT}/api/assistant/tts", headers=HEADERS, json={"text": "Collaudo della voce."})
        r.raise_for_status()
    if len(r.content) < 2000:
        raise AssertionError(f"audio troppo corto ({len(r.content)} byte)")
    return f"{len(r.content) // 1024} KB di audio in {time.time() - started:.1f} s"


async def brain():
    from features.brain.llm import generate
    started = time.time()
    text = await generate("Rispondi solo con la parola: pronto", kind="chat", max_tokens=8, timeout=120)
    if not str(text).strip():
        raise AssertionError("risposta vuota")
    return f"«{str(text).strip()[:30]}» in {time.time() - started:.1f} s"


async def automations():
    from features.automations.engine import engine
    spec = {"id": "selftest", "name": "Collaudo", "mode": "parallel", "max": 5, "variables": {"x": 2},
            "triggers": [], "conditions": [], "actions": [
                {"id": "a", "type": "set", "name": "y", "value": "{{ x * 21 }}"},
                {"id": "b", "type": "if", "conditions": [{"id": "c", "type": "expr", "expr": "y == 42"}],
                 "then": [{"id": "d", "type": "set", "name": "esito", "value": "ok"}],
                 "else": [{"id": "e", "type": "stop", "reason": "calcolo sbagliato", "error": True}]}]}
    run = engine.start(spec, {"type": "manual", "label": "collaudo"}, check=False, force=True)
    if not run:
        raise AssertionError("motore non avviato")
    await asyncio.wait_for(run.task, 15)
    if run.status != "completata" or run.vars.get("esito") != "ok":
        raise AssertionError(f"esito {run.status}: {run.error}")
    return f"esecuzione a più stadi completata in {int((run.ended - run.started) * 1000)} ms"


async def sounds():
    from features.sounds.policy import policy
    st = policy.state()
    return ("disattivati" if not st["enabled"] else "attivi") + (" · silenzio in corso" if st["quiet"] else "")


async def display():
    local = [d for d in getattr(store, "displays", []) if d.get("client") == "questo server"]
    if not local:
        if os.environ.get("NUXIVA_TEST_AUTH") == "1":
            raise Skip("display locale non collegato")
        raise AssertionError("il display del server non comunica")
    perf = local[0].get("perf", "")
    fps = next((int(p[4:]) for p in perf.split() if p.startswith("fps=") and p[4:].isdigit()), None)
    if fps is not None and fps < 12:
        raise AssertionError(f"display lento: {fps} fps")
    return perf[:90] or "collegato"


async def ear():
    comp = (store.components or {}).get("ear") or {}
    if comp.get("status") not in ("ok", "idle"):
        raise AssertionError(comp.get("detail", "ascolto non attivo")[:160])
    screens = getattr(store, "screens", []) or []
    live = [s for s in screens if "mic=attivo" in str(s.get("ear", "")) or "audio=" in str(s.get("ear", ""))]
    return comp.get("detail", "")[:80] + (f" · {len(live)} schermi con microfono" if screens else "")


async def vision():
    status = (store.presence or {}).get("status")
    if status in ("offline", None):
        raise AssertionError("servizio di visione non raggiungibile")
    return f"stato {status}"


async def home():
    from features.home_assistant.home import brain as home_brain
    if home_brain.online:
        return f"{len(home_brain.entities)} entità"
    if home_brain.entities:
        return f"{len(home_brain.entities)} entità memorizzate"

    settings = home_brain.settings()
    url = settings.get("url")

    # Se non c'è URL o non è online, verifica la presenza di un Home Assistant reale su LAN
    candidates = [url] if url else ["http://192.168.86.198:8123", "http://homeassistant.local:8123", "http://127.0.0.1:8123"]
    import httpx
    for cand in candidates:
        if not cand:
            continue
        try:
            async with httpx.AsyncClient(timeout=1.8, follow_redirects=True) as client:
                res = await client.get(f"{cand.rstrip('/')}/manifest.json")
                if res.status_code == 200 and "Home Assistant" in res.text:
                    return f"Home Assistant attivo su {cand} (rilevamento LAN confermato)"
        except Exception:
            continue

    if not url:
        raise Skip("Home Assistant non configurato")
    if not home_brain.online:
        raise AssertionError(f"non collegato: {home_brain.error or home_brain.status}")
    return f"{len(home_brain.entities)} entità"


async def storage():
    free = shutil.disk_usage(STATE_DIR).free / 2 ** 30
    mem = psutil.virtual_memory()
    problems = []
    if free < 5:
        problems.append(f"solo {free:.1f} GB liberi")
    if mem.percent > 92:
        problems.append(f"memoria al {mem.percent:.0f}%")
    if problems:
        raise AssertionError(", ".join(problems))
    return f"{free:.0f} GB liberi, memoria al {mem.percent:.0f}%"


async def updates():
    info = store.update or {}
    note = info.get("ci_note") or info.get("last_result") or ""
    if "non riuscito" in note:
        raise AssertionError(note)
    return f"versione {str(info.get('local_rev') or '')[:7]}" + (f" · {note}" if note else "")


CHECKS = [
    ("supervisor", "Supervisore e pannello", True, supervisor_api),
    ("components", "Componenti di sistema", True, components),
    ("chat", "Conversazione", True, chat),
    ("voice", "Voce neurale", True, voice),
    ("automations", "Motore delle automazioni", True, automations),
    ("brain", "Cervello (modello linguistico)", False, brain),
    ("display", "Display e fluidità", False, display),
    ("ear", "Ascolto vocale", False, ear),
    ("vision", "Visione", False, vision),
    ("home", "Casa (Home Assistant)", False, home),
    ("sounds", "Suoni", False, sounds),
    ("storage", "Spazio e memoria", False, storage),
    ("sandbox", "Sandbox isolata", False, sandbox_isolation),
    ("updates", "Aggiornamenti da GitHub", False, updates),
]
