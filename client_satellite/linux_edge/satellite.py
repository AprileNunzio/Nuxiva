#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import logging
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

VERSION = "5.8.9"
DISCOVER_PORT = 50505
JOIN_TIMEOUT = 15 * 60
REDISCOVER_AFTER = 3
CONFIG = Path(os.environ.get("NUXIVA_NODE_CONFIG", Path.home() / ".config" / "nuxiva-node.json"))
SERVICE = Path("/etc/systemd/system/nuxiva-node.service")
UPDATE_STATE = CONFIG.with_name("nuxiva-node-update.json")
TYPES = ("satellite", "display", "server", "esp32", "android", "sensor", "other")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("nuxiva-node")


def device_key(seed: str):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("Chiave del nodo non valida: abbina di nuovo il nodo")
    return Ed25519PrivateKey.from_private_bytes(bytes.fromhex(seed))


def public_hex(seed: str) -> str:
    from cryptography.hazmat.primitives import serialization as ser
    return device_key(seed).public_key().public_bytes(ser.Encoding.Raw, ser.PublicFormat.Raw).hex()


def proof(seed: str, node: str, path: str, data: bytes) -> dict:
    ts, nonce = str(int(time.time())), secrets.token_hex(16)
    msg = "\n".join(("nuxiva-node-v1", node, "POST", path, ts, nonce, hashlib.sha256(data).hexdigest())).encode()
    return {"X-Nuxiva-Node": node, "X-Nuxiva-Ts": ts, "X-Nuxiva-Nonce": nonce, "X-Nuxiva-Sig": device_key(seed).sign(msg).hex()}


def post(server: str, path: str, body: dict, headers: dict | None = None, seed: str = "", node: str = "") -> dict:
    data = json.dumps(body).encode()
    signed = proof(seed, node, path, data) if seed else {}
    req = urllib.request.Request(f"{server}{path}", data=data, method="POST",
                                 headers={"Content-Type": "application/json", **(headers or {}), **signed})
    with urllib.request.urlopen(req, timeout=15) as res:
        return json.loads(res.read() or b"{}")


def save_config(cfg: dict) -> None:
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(CONFIG, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as handle:
        json.dump(cfg, handle)


def node_id(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", f"{socket.gethostname()}-{name}".lower()).strip("-")
    return (base or "nodo")[:40]


def metrics() -> dict:
    out = {}
    with open("/proc/loadavg") as f:
        out["cpu"] = min(100.0, float(f.read().split()[0]) * 100 / (os.cpu_count() or 1))
    mem = dict(line.split(":", 1) for line in Path("/proc/meminfo").read_text().splitlines() if ":" in line)
    total, avail = int(mem["MemTotal"].split()[0]), int(mem["MemAvailable"].split()[0])
    out["ram"] = (total - avail) * 100 / total
    disk = shutil.disk_usage("/")
    out["disk"] = disk.used * 100 / disk.total
    out["uptime"] = float(Path("/proc/uptime").read_text().split()[0])
    zone = Path("/sys/class/thermal/thermal_zone0/temp")
    if zone.exists():
        out["temp"] = int(zone.read_text()) / 1000
    probe_extra(out)
    return out


PROBE = {"energy": None, "rtt": None}


def sysfs(path: str | Path) -> str:
    try:
        return Path(path).read_text().strip()
    except OSError:
        return ""


def number(path: str) -> float | None:
    try:
        return float(sysfs(path))
    except ValueError:
        return None


def probe_extra(out: dict) -> None:
    now, energy = time.monotonic(), number("/sys/class/powercap/intel-rapl:0/energy_uj")
    if energy is not None and PROBE["energy"] and energy >= PROBE["energy"][0]:
        out["power_w"] = (energy - PROBE["energy"][0]) / 1e6 / max(now - PROBE["energy"][1], 1e-3)
    PROBE["energy"] = (energy, now) if energy is not None else None
    found = {"gpu": number("/sys/class/drm/card0/device/gpu_busy_percent"), "battery": number("/sys/class/power_supply/BAT0/capacity"), "rtt_ms": PROBE["rtt"]}
    out.update({key: value for key, value in found.items() if value is not None})


HARDWARE = {"at": 0.0, "data": {}}
STATE = {"adapted": False, "vitals": False}
HARDWARE_TTL = 120.0
CARD_RE = re.compile(r"^card \d+: [^\[]*\[([^\]]+)\]", re.M)


def run_text(args: list[str], timeout: float = 6.0) -> str:
    if not shutil.which(args[0]):
        return ""
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def video_devices() -> tuple[list[str], bool]:
    names, ir = [], False
    for line in run_text(["v4l2-ctl", "--list-devices"]).splitlines():
        if line and not line[0].isspace():
            current = line.strip().rstrip(":")
            names.append(current)
            ir = ir or bool(re.search(r"\b(ir|infrared|infra-red)\b", current, re.I))
    for node in sorted(Path("/dev").glob("video*"))[:8]:
        if "GREY" in run_text(["v4l2-ctl", "-d", str(node), "--list-formats"]).upper():
            ir = True
    return names[:12], ir


def usb_products() -> list[str]:
    return [name for name in (sysfs(p) for p in sorted(Path("/sys/bus/usb/devices").glob("*/product"))[:40]) if name][:12]


def hardware(force: bool = False) -> dict:
    if not force and time.time() - HARDWARE["at"] < HARDWARE_TTL and HARDWARE["data"]:
        return HARDWARE["data"]
    mem = dict(line.split(":", 1) for line in Path("/proc/meminfo").read_text().splitlines() if ":" in line)
    cpuinfo = Path("/proc/cpuinfo").read_text() if Path("/proc/cpuinfo").exists() else ""
    cameras, ir = video_devices()
    gpu = run_text(["nvidia-smi", "-L"]).splitlines()[:1]
    disk = shutil.disk_usage("/")
    HARDWARE["data"] = {
        "cores": os.cpu_count() or 1, "ram_gb": round(int(mem["MemTotal"].split()[0]) / 1048576, 1),
        "disk_gb": round(disk.total / 2 ** 30), "avx2": "avx2" in cpuinfo, "arch": os.uname().machine,
        "os": (Path("/etc/os-release").read_text().split("PRETTY_NAME=")[-1].split("\n")[0].strip('"') if Path("/etc/os-release").exists() else ""),
        "gpu": gpu[0].split(" (UUID")[0] if gpu else "", "cameras": cameras, "ir_camera": ir,
        "audio_in": CARD_RE.findall(run_text(["arecord", "-l"]))[:12], "audio_out": CARD_RE.findall(run_text(["aplay", "-l"]))[:12],
        "bluetooth": Path("/sys/class/bluetooth").exists(), "usb": usb_products()}
    HARDWARE["at"] = time.time()
    return HARDWARE["data"]


def capabilities() -> list[str]:
    caps = []
    if shutil.which("arecord") and list(Path("/proc/asound").glob("card*")):
        caps.append("audio")
    if list(Path("/dev").glob("video*")):
        caps.append("camera")
    if hardware().get("ir_camera"):
        caps.append("ir_camera")
    if Path("/sys/class/bluetooth").exists():
        caps.append("bluetooth")
        if importlib.util.find_spec("bleak"):
            caps.append("vitals_ble")
    return caps


def discover(ident: str = "", paired: bool = False, timeout: float = 4.0) -> str | None:
    hello = json.dumps({"nuxiva": "discover", "id": ident, "paired": paired, "version": VERSION}).encode()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(timeout)
        try:
            sock.sendto(hello, ("255.255.255.255", DISCOVER_PORT))
            while True:
                data, addr = sock.recvfrom(1024)
                msg = json.loads(data)
                if isinstance(msg, dict) and msg.get("nuxiva") == "master":
                    port = int(msg.get("port") or 80)
                    return f"http://{addr[0]}" + ("" if port == 80 else f":{port}")
        except (OSError, ValueError):
            return None


def own_sha() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def update_state(**changes) -> dict:
    try:
        state = json.loads(UPDATE_STATE.read_text())
    except (OSError, ValueError):
        state = {}
    if changes:
        state.update(changes)
        UPDATE_STATE.write_text(json.dumps(state))
    return state


def update_failed(code: str, **extra) -> None:
    update_state(state="failed", last_error={"code": code, "at": int(time.time())}, **extra)
    log.warning("Aggiornamento dell'agente non applicato: %s", code)


def restart() -> None:
    os.execv(sys.executable, [sys.executable, __file__, *sys.argv[1:]])


def self_update(cfg: dict, expected: str) -> None:
    update_state(state="downloading", last_check=int(time.time()))
    try:
        with urllib.request.urlopen(f"{cfg['server']}/nodes/agent.py", timeout=30) as res:
            code = res.read()
    except (urllib.error.URLError, OSError):
        return update_failed("download_failed")
    if hashlib.sha256(code).hexdigest() != expected:
        return update_failed("hash_mismatch")
    staged, backup = Path(__file__).with_suffix(".new"), Path(__file__).with_suffix(".bak")
    staged.write_bytes(code)
    probe = subprocess.run([sys.executable, str(staged), "--selftest"], capture_output=True, timeout=30, check=False)
    if probe.returncode != 0:
        staged.unlink()
        return update_failed("selftest_failed")
    backup.write_bytes(Path(__file__).read_bytes())
    os.replace(staged, __file__)
    update_state(state="installing", boots=0, target_sha=expected)
    log.info("Agente aggiornato: riavvio")
    restart()


def settle_update() -> None:
    state, backup = update_state(), Path(__file__).with_suffix(".bak")
    if state.get("state") != "installing":
        return
    if state.get("boots", 0) >= 2 and backup.exists():
        os.replace(backup, __file__)
        update_state(state="rolled_back", bad_sha=state.get("target_sha"), last_error={"code": "boot_failed", "at": int(time.time())})
        restart()
    update_state(boots=state.get("boots", 0) + 1)


def confirm_update() -> None:
    if update_state().get("state") == "installing":
        update_state(state="idle", boots=0, last_success=int(time.time()), last_error=None)


def update_report() -> dict:
    state = update_state()
    return {"channel": "debian", "version": VERSION, "last_check": int(time.time()), "state": state.get("state", "idle"),
            **{key: state[key] for key in ("last_success", "last_error") if state.get(key)}}


def run_command(cmd: str, cfg: dict) -> None:
    log.info("Comando dal server: %s", cmd)
    if cmd == "identify":
        for _ in range(3):
            sys.stdout.write("\a")
            sys.stdout.flush()
            time.sleep(0.4)
        if shutil.which("espeak-ng"):
            subprocess.run(["espeak-ng", "-v", "it", f"Sono {cfg['name']}"], check=False)
    elif cmd == "adapt":
        hardware(force=True)
        STATE["adapted"] = True
    elif cmd == "update" and cfg.get("agent"):
        self_update(cfg, cfg["agent"])
    elif cmd == "restart":
        restart()
    elif cmd == "reboot" and os.geteuid() == 0:
        subprocess.run(["systemctl", "reboot"], check=False)


def pair(args) -> dict:
    ident = node_id(args.name)
    seed = secrets.token_hex(32)
    res = post(args.server, "/api/nodes/pair", {"code": args.code, "id": ident, "name": args.name, "type": args.type,
                                                "room": args.room, "pubkey": public_hex(seed)})
    cfg = {"server": args.server, "id": ident, "token": res["token"], "name": args.name, "key": seed}
    save_config(cfg)
    log.info("Abbinato a %s come %s", args.server, ident)
    return cfg


def join(args) -> dict:
    server = args.server or discover(node_id(args.name))
    if not server:
        sys.exit("Nessun server Nuxiva trovato in rete: indica --server http://IP-DI-NUXIVA")
    ident, seed = node_id(args.name), secrets.token_hex(32)
    res = post(server, "/api/nodes/request", {"id": ident, "pubkey": public_hex(seed), "name": args.name,
                                              "type": args.type, "room": args.room})
    log.info("Richiesta inviata a %s. Nel pannello Nodi approva il codice %s", server, res["fingerprint"])
    print(f"Codice da confermare nel pannello Nuxiva: {res['fingerprint']}", flush=True)
    deadline = time.time() + JOIN_TIMEOUT
    while time.time() < deadline:
        time.sleep(5)
        claim = post(server, "/api/nodes/claim", {"id": ident}, seed=seed, node=ident)
        if claim.get("approved"):
            cfg = {"server": server, "id": ident, "token": claim["token"], "name": args.name, "key": seed}
            save_config(cfg)
            log.info("Nodo approvato e abbinato come %s", ident)
            return cfg
    sys.exit("Richiesta scaduta: nessuno l'ha approvata nel pannello")


def install_service() -> None:
    if os.geteuid() != 0:
        sys.exit("Per installare il servizio esegui con sudo")
    unit = ("[Unit]", "Description=Nodo Nuxiva", "After=network-online.target", "Wants=network-online.target", "", "[Service]",
            f"Environment=NUXIVA_NODE_CONFIG={CONFIG}", f"ExecStart={sys.executable} {Path(__file__).resolve()}", "Restart=always",
            "RestartSec=10", "", "[Install]", "WantedBy=multi-user.target", "")
    SERVICE.write_text("\n".join(unit))
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "enable", "--now", "nuxiva-node"], check=True)
    log.info("Servizio nuxiva-node installato e avviato")


def fetch_module(cfg: dict, name: str, expected: str):
    path = CONFIG.with_name(f"nuxiva-node-{name}.py")
    with urllib.request.urlopen(f"{cfg['server']}/nodes/{name}.py", timeout=30) as res:
        code = res.read()
    if hashlib.sha256(code).hexdigest() != expected:
        log.warning("Modulo %s scartato: impronta non corrispondente", name)
        return None
    path.write_bytes(code)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def start_vitals(cfg: dict, expected: str) -> None:
    if importlib.util.find_spec("bleak") and (module := fetch_module(cfg, "vitals_ble", expected)):
        module.start(cfg, post)
        STATE["vitals"] = True


def loop(cfg: dict) -> None:
    settle_update()
    headers = {"Authorization": f"Bearer {cfg['token']}", "X-Nuxiva-Node": cfg["id"]}
    wait, failures = 30, 0
    while True:
        try:
            adapted, STATE["adapted"] = STATE["adapted"], False
            started = time.monotonic()
            res = post(cfg["server"], "/api/nodes/heartbeat", {"version": VERSION, "hostname": socket.gethostname(),
                                                             "metrics": metrics(), "capabilities": capabilities(),
                                                             "hardware": hardware(force=adapted), "adapted": adapted,
                                                             "update": update_report()}, headers,
                       cfg.get("key", ""), cfg["id"])
            wait, failures = int(res.get("heartbeat") or 30), 0
            PROBE["rtt"] = (time.monotonic() - started) * 1000
            cfg["agent"] = res.get("agent") or ""
            confirm_update()
            if not STATE["vitals"] and (wanted := (res.get("modules") or {}).get("vitals_ble")):
                start_vitals(cfg, wanted)
            if cfg["agent"] and cfg["agent"] not in (own_sha(), update_state().get("bad_sha")):
                self_update(cfg, cfg["agent"])
            for cmd in res.get("commands") or []:
                run_command(cmd, cfg)
            if STATE["adapted"]:
                wait = 1
            settings = res.get("settings")
            if isinstance(settings, dict) and settings != cfg.get("settings"):
                cfg["settings"] = settings
                save_config({k: v for k, v in cfg.items() if k != "agent"})
                log.info("Impostazioni aggiornate dal server (%d personalizzate)", len(res.get("custom") or []))
        except urllib.error.HTTPError as exc:
            if exc.code == 401 and b"node.error." not in exc.read(512):
                sys.exit("Il server ha revocato questo nodo: abbinalo di nuovo")
            log.warning("Server non disponibile: %s", exc)
        except (urllib.error.URLError, OSError) as exc:
            failures += 1
            log.warning("Server non raggiungibile: %s", exc)
            if failures >= REDISCOVER_AFTER:
                found = discover(cfg["id"], paired=True)
                if found and found != cfg["server"]:
                    log.info("Il server Nuxiva ha cambiato indirizzo: %s", found)
                    cfg["server"] = found
                    save_config({k: v for k, v in cfg.items() if k != "agent"})
                failures = 0
        time.sleep(wait)


def main() -> None:
    parser = argparse.ArgumentParser(description="Agente dei nodi Nuxiva")
    parser.add_argument("--server", help="Indirizzo del server Nuxiva, es. http://192.168.1.10")
    parser.add_argument("--code", help="Codice di abbinamento mostrato nel pannello Nodi")
    parser.add_argument("--name", default=socket.gethostname())
    parser.add_argument("--room", default="")
    parser.add_argument("--type", default="satellite", choices=TYPES)
    parser.add_argument("--install", action="store_true", help="Installa l'agente come servizio di sistema")
    parser.add_argument("--join", action="store_true", help="Cerca Nuxiva in rete e chiedi l'approvazione dal pannello")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        print(VERSION)
        return
    if args.code and args.server:
        cfg = pair(args)
    elif args.join:
        cfg = join(args)
    elif CONFIG.exists():
        cfg = json.loads(CONFIG.read_text())
    else:
        sys.exit("Prima abbina il nodo: --join (automatico) oppure --server http://IP-DI-NUXIVA --code CODICE")
    if args.install:
        install_service()
        return
    loop(cfg)


if __name__ == "__main__":
    main()
