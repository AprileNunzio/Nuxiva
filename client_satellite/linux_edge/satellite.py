#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
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

VERSION = "5.3.0"
DISCOVER_PORT = 50505
ANNOUNCE_PORT = 50506
JOIN_TIMEOUT = 15 * 60
REDISCOVER_AFTER = 3
CONFIG = Path(os.environ.get("NUXIVA_NODE_CONFIG", Path.home() / ".config" / "nuxiva-node.json"))
SERVICE = Path("/etc/systemd/system/nuxiva-node.service")
TYPES = ("satellite", "display", "server", "esp32", "android", "sensor", "other")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("nuxiva-node")


def post(server: str, path: str, body: dict, headers: dict | None = None) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(f"{server}{path}", data=data, method="POST",
                                 headers={"Content-Type": "application/json", **(headers or {})})
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
    return out


HARDWARE = {"at": 0.0, "data": {}}
STATE = {"adapted": False}
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
    out = []
    for p in sorted(Path("/sys/bus/usb/devices").glob("*/product"))[:40]:
        try:
            out.append(p.read_text().strip())
        except OSError:
            continue
    return out[:12]


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


def self_update(cfg: dict, expected: str) -> None:
    with urllib.request.urlopen(f"{cfg['server']}/nodes/agent.py", timeout=30) as res:
        code = res.read()
    if hashlib.sha256(code).hexdigest() != expected:
        log.warning("Aggiornamento dell'agente scartato: impronta non corrispondente")
        return
    Path(__file__).write_bytes(code)
    log.info("Agente aggiornato: riavvio")
    os.execv(sys.executable, [sys.executable, __file__, *sys.argv[1:]])


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
        os.execv(sys.executable, [sys.executable, __file__, *sys.argv[1:]])
    elif cmd == "reboot" and os.geteuid() == 0:
        subprocess.run(["systemctl", "reboot"], check=False)


def pair(args) -> dict:
    ident = node_id(args.name)
    res = post(args.server, "/api/nodes/pair",
               {"code": args.code, "id": ident, "name": args.name, "type": args.type, "room": args.room})
    cfg = {"server": args.server, "id": ident, "token": res["token"], "name": args.name}
    save_config(cfg)
    log.info("Abbinato a %s come %s", args.server, ident)
    return cfg


def join(args) -> dict:
    server = args.server or discover(node_id(args.name))
    if not server:
        sys.exit("Nessun server Nuxiva trovato in rete: indica --server http://IP-DI-NUXIVA")
    ident, key = node_id(args.name), secrets.token_hex(32)
    res = post(server, "/api/nodes/request", {"id": ident, "key": key, "name": args.name, "type": args.type,
                                              "room": args.room})
    log.info("Richiesta inviata a %s. Nel pannello Nodi approva il codice %s", server, res["fingerprint"])
    print(f"Codice da confermare nel pannello Nuxiva: {res['fingerprint']}", flush=True)
    deadline = time.time() + JOIN_TIMEOUT
    while time.time() < deadline:
        time.sleep(5)
        claim = post(server, "/api/nodes/claim", {"id": ident, "key": key})
        if claim.get("approved"):
            cfg = {"server": server, "id": ident, "token": claim["token"], "name": args.name}
            save_config(cfg)
            log.info("Nodo approvato e abbinato come %s", ident)
            return cfg
    sys.exit("Richiesta scaduta: nessuno l'ha approvata nel pannello")


def install_service() -> None:
    if os.geteuid() != 0:
        sys.exit("Per installare il servizio esegui con sudo")
    SERVICE.write_text(f"""[Unit]
Description=Nodo Nuxiva
After=network-online.target
Wants=network-online.target

[Service]
Environment=NUXIVA_NODE_CONFIG={CONFIG}
ExecStart={sys.executable} {Path(__file__).resolve()}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
""")
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "enable", "--now", "nuxiva-node"], check=True)
    log.info("Servizio nuxiva-node installato e avviato")


HR_CHAR = "00002a37-0000-1000-8000-00805f9b34fb"
TEMP_CHAR = "00002a1c-0000-1000-8000-00805f9b34fb"
PLX_CHARS = ("00002a5e-0000-1000-8000-00805f9b34fb", "00002a5f-0000-1000-8000-00805f9b34fb")
VITALS_SCAN = 5.0
VITALS_PAUSE = 3.0


def sfloat(raw: int) -> float | None:
    if raw in (0x07FF, 0x0800, 0x0801, 0x07FE, 0x0802):
        return None
    mantissa, exponent = raw & 0x0FFF, raw >> 12
    mantissa -= 0x1000 if mantissa >= 0x800 else 0
    exponent -= 0x10 if exponent >= 0x8 else 0
    return mantissa * 10 ** exponent


def ieee_float(raw: int) -> float | None:
    if raw in (0x007FFFFF, 0x00800000, 0x00800001, 0x007FFFFE, 0x00800002):
        return None
    mantissa, exponent = raw & 0xFFFFFF, raw >> 24
    mantissa -= 0x1000000 if mantissa >= 0x800000 else 0
    exponent -= 0x100 if exponent >= 0x80 else 0
    return mantissa * 10 ** exponent


def parse_heart_rate(data: bytes) -> list[tuple[str, float]]:
    if len(data) < (3 if data and data[0] & 1 else 2):
        return []
    return [("heart_rate", int.from_bytes(data[1:3], "little") if data[0] & 1 else data[1])]


def parse_temperature(data: bytes) -> list[tuple[str, float]]:
    if len(data) < 5:
        return []
    value = ieee_float(int.from_bytes(data[1:5], "little"))
    if value is None:
        return []
    return [("body_temp", round((value - 32) * 5 / 9 if data[0] & 1 else value, 1))]


def parse_oximeter(data: bytes) -> list[tuple[str, float]]:
    if len(data) < 5:
        return []
    spo2, pulse = sfloat(int.from_bytes(data[1:3], "little")), sfloat(int.from_bytes(data[3:5], "little"))
    rows = [("spo2", round(spo2))] if spo2 is not None else []
    return rows + ([("heart_rate", round(pulse))] if pulse is not None else [])


PARSERS = {HR_CHAR: parse_heart_rate, TEMP_CHAR: parse_temperature, PLX_CHARS[0]: parse_oximeter, PLX_CHARS[1]: parse_oximeter}


async def vitals_cycle(cfg: dict, headers: dict, state: dict) -> None:
    import asyncio
    from bleak import BleakClient, BleakScanner
    found = await BleakScanner.discover(timeout=VITALS_SCAN, return_adv=True)
    watch = set(state["watch"])
    seen = [{"address": a.upper(), "rssi": adv.rssi} for a, (_, adv) in found.items() if a.upper() in watch][:40]
    samples, state["samples"] = state["samples"][:200], state["samples"][200:]
    res = await asyncio.to_thread(post, cfg["server"], "/api/vitals/node", {"seen": seen, "samples": samples}, headers)
    state["watch"] = [str(a).upper() for a in res.get("watch") or []]
    wanted = {str(a).upper() for a in res.get("connect") or []}
    for address in list(state["clients"]):
        if address not in wanted or not state["clients"][address].is_connected:
            client = state["clients"].pop(address)
            try:
                await client.disconnect()
            except Exception as exc:
                log.info("Disconnessione BLE %s: %s", address, exc)
    for address in wanted - set(state["clients"]):
        client = BleakClient(address)
        try:
            await client.connect(timeout=10.0)
            for char, parser in PARSERS.items():
                if client.services.get_characteristic(char):
                    def notify(_, data, address=address, parser=parser):
                        now = time.time()
                        state["samples"].extend({"address": address, "metric": m, "value": v, "ts": now} for m, v in parser(bytes(data)))
                    await client.start_notify(char, notify)
            state["clients"][address] = client
        except Exception as exc:
            log.info("Connessione BLE a %s non riuscita: %s", address, exc)


def vitals_loop(cfg: dict) -> None:
    import asyncio
    headers = {"Authorization": f"Bearer {cfg['token']}", "X-Nuxiva-Node": cfg["id"]}
    state = {"watch": [], "clients": {}, "samples": []}

    async def run() -> None:
        while True:
            try:
                await vitals_cycle(cfg, headers, state)
            except Exception as exc:
                log.info("Ciclo parametri vitali: %s", exc)
            await asyncio.sleep(VITALS_PAUSE)
    asyncio.run(run())


def start_vitals(cfg: dict) -> None:
    try:
        import bleak
    except ImportError:
        return
    del bleak
    import threading
    threading.Thread(target=vitals_loop, args=(cfg,), daemon=True, name="vitals").start()
    log.info("Lettura dei parametri vitali via Bluetooth attiva")


def loop(cfg: dict) -> None:
    start_vitals(cfg)
    headers = {"Authorization": f"Bearer {cfg['token']}", "X-Nuxiva-Node": cfg["id"]}
    wait, failures = 30, 0
    while True:
        try:
            adapted, STATE["adapted"] = STATE["adapted"], False
            res = post(cfg["server"], "/api/nodes/heartbeat", {"version": VERSION, "hostname": socket.gethostname(),
                                                             "metrics": metrics(), "capabilities": capabilities(),
                                                             "hardware": hardware(force=adapted), "adapted": adapted}, headers)
            wait, failures = int(res.get("heartbeat") or 30), 0
            cfg["agent"] = res.get("agent") or ""
            if cfg["agent"] and cfg["agent"] != own_sha():
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
            if exc.code == 401:
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
    args = parser.parse_args()
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
