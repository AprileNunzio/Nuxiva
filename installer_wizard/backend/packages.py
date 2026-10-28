import glob
import json
import os
import time
from dataclasses import dataclass

import machine
from config import STATE_DIR, ollama_remote, read_env, write_env

DEMO: bool = True
from state import store

MARK_FILE = STATE_DIR / "packages.json"
BRAIN_MODES = ("local", "remote", "cloud")


@dataclass(frozen=True)
class Package:
    id: str
    steps: tuple[str, ...]
    env: str
    title: str
    description: str
    size_gb: float
    detect: str = ""
    removable: bool = True
    auto: bool = False


PACKAGES = (
    Package("display", ("kiosk",), "NUXIVA_KIOSK", "Display", "Schermo a tutto campo con volto, widget e lavagna", 0.4, "monitor"),
    Package("voice", ("voice",), "NUXIVA_VOICE_PACKAGE", "Voce", "Nuxiva ti risponde parlando, voce neurale offline", 1.0,
            removable=False),
    Package("ear", ("ear",), "NUXIVA_EAR", "Ascolto", "Ti ascolta dal microfono e risponde a «Ehi, Nuxiva»", 1.5),
    Package("music", ("music",), "NUXIVA_MUSIC_ID", "Riconoscimento musicale", "Brano, artista e album della musica in ascolto", 0.3),
    Package("vision", ("vision",), "NUXIVA_VISION", "Visione", "Riconosce chi ha davanti dalla webcam, tutto in locale", 1.0, "camera"),
    Package("bluetooth", ("bluetooth",), "NUXIVA_BLUETOOTH", "Bluetooth", "Casse, cuffie e microfoni senza fili", 0.05, "bluetooth"),
    Package("documents", ("office",), "NUXIVA_DOCUMENTS", "Documenti Office", "Crea e apre Word, Excel, PowerPoint e PDF", 1.5),
    Package("convert3d", ("convert3d",), "NUXIVA_3D_CONVERT", "Conversione 3D", "Apre file BLEND, USD e DWG", 1.0),
    Package("shares", ("shares",), "NUXIVA_SHARES", "Cartelle condivise", "Cartelle visibili da Windows e Mac", 0.05),
    Package("sandbox", ("sandbox", "gvisor", "firecracker"), "NUXIVA_SANDBOX", "Sandbox", "Esegue in sicurezza il codice che Nuxiva scrive", 0.6,
            removable=False),
    Package("native", ("native",), "NUXIVA_NATIVE", "Core nativo", "Componenti in Rust più veloci, con ritorno automatico a Python", 0.3,
            auto=True),
    Package("brain_local", ("ollama", "brain", "soup"), "NUXIVA_BRAIN", "Cervello locale", "Modelli linguistici su questo computer con Ollama", 8.0,
            removable=False),
    Package("brain_models", ("models", "warmup"), "NUXIVA_BRAIN", "Modelli del cervello", "Scarica e prepara i modelli scelti", 2.0),
    Package("voicestudio", ("voicestudio",), "NUXIVA_VOICESTUDIO", "Studio delle voci", "Voci personalizzate con VoiceStudio", 6.0),
)
PACKAGE_BY_ID = {p.id: p for p in PACKAGES}
PACKAGE_BY_STEP = {s: p for p in PACKAGES for s in p.steps}
ON = ("1", "on", "yes", "true", "auto")


def _detect(kind: str) -> bool:
    if os.environ.get("NUXIVA_TEST_AUTH") == "1":
        return True
    if kind == "monitor":
        return any(open(p).read().strip() == "connected" for p in glob.glob("/sys/class/drm/card*-*/status") if os.access(p, os.R_OK))
    if kind == "camera":
        return bool(glob.glob("/dev/video*"))
    if kind == "bluetooth":
        return bool(glob.glob("/sys/class/bluetooth/hci*"))
    return False


def brain_mode(env: dict | None = None) -> str:
    env = read_env() if env is None else env
    mode = env.get("NUXIVA_BRAIN", "").strip().lower()
    if mode in BRAIN_MODES:
        return mode
    if ollama_remote():
        return "remote"
    if DEMO or _installed("ollama"):
        return "local"
    return "pending"


def _installed(step_id: str) -> bool:
    return (store.steps.get(step_id) or {}).get("status") == "done"


def wanted(pkg: Package, env: dict | None = None) -> bool:
    env = read_env() if env is None else env
    if pkg.env == "NUXIVA_BRAIN":
        mode = brain_mode(env)
        return mode == "local" if pkg.id == "brain_local" else mode in ("local", "remote")
    value = env.get(pkg.env, "").strip().lower()
    if value:
        return value in ON
    if pkg.auto:
        return not machine.heavy(pkg.id, env)
    return bool(pkg.detect) and _detect(pkg.detect)


def explicit(pkg: Package, env: dict | None = None) -> bool:
    env = read_env() if env is None else env
    return bool(env.get(pkg.env, "").strip())


def step_wanted(step_id: str, env: dict | None = None) -> bool:
    pkg = PACKAGE_BY_STEP.get(step_id)
    if pkg is None:
        return True
    if explicit(pkg, env) and not wanted(pkg, env):
        return False
    return wanted(pkg, env) or _installed(step_id)


def migrate() -> dict:
    if MARK_FILE.exists():
        return {}
    env = read_env()
    updates = {}
    for pkg in PACKAGES:
        if pkg.env == "NUXIVA_BRAIN" or explicit(pkg, env):
            continue
        if any(_installed(s) for s in pkg.steps):
            updates[pkg.env] = "1"
    if not env.get("NUXIVA_BRAIN") and (_installed("ollama") or _installed("models")):
        updates["NUXIVA_BRAIN"] = "remote" if ollama_remote() else "local"
    if updates:
        write_env(updates)
        store.event("INFO", f"Pacchetti già installati confermati: {', '.join(sorted(updates))}", "packages")
    _mark()
    return updates


def _mark() -> None:
    MARK_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = MARK_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps({"version": 1, "at": int(time.time())}), encoding="utf-8")
    os.replace(tmp, MARK_FILE)


def state(pkg: Package, env: dict | None = None) -> str:
    env = read_env() if env is None else env
    statuses = [(store.steps.get(s) or {}).get("status", "") for s in pkg.steps]
    if any(s in ("running", "checking", "retrying") for s in statuses):
        return "installing"
    if not wanted(pkg, env):
        return "removed" if explicit(pkg, env) else "available"
    if statuses[0] == "done":
        return "installed"
    if any(s == "failed" for s in statuses):
        return "failed"
    return "queued"


def catalog() -> list[dict]:
    env = read_env()
    return [{"id": p.id, "title": p.title, "description": p.description, "size_gb": p.size_gb, "steps": list(p.steps),
             "state": state(p, env), "wanted": wanted(p, env), "removable": p.removable, "detected": bool(p.detect) and _detect(p.detect),
             "heavy": machine.heavy(p.id, env)}
            for p in PACKAGES if p.id != "brain_models"]


def request_updates(pkg_id: str, on: bool) -> dict:
    pkg = PACKAGE_BY_ID.get(pkg_id)
    if pkg is None or pkg.id == "brain_models" or (not on and not pkg.removable):
        raise KeyError(pkg_id)
    if pkg.env == "NUXIVA_BRAIN":
        return {"NUXIVA_BRAIN": "local"}
    return {pkg.env: "1" if on else "0"}
