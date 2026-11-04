import asyncio
import os
import re
import shutil
import signal
import time
from pathlib import Path

from config import STATE_DIR
from state import store

AUDIT = STATE_DIR / "debian_audit.log"
AUDIT_CAP = 1_000_000
SSH_DIR = STATE_DIR / "ssh"
OUT_TAIL = 6000
PACKAGE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9+.:~=/_-]{0,100}$")
UNIT_RE = re.compile(r"^[A-Za-z0-9@._:\\-]{1,100}$")
HOST_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,252}$")
USER_RE = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")
SERVICE_ACTIONS = ("start", "stop", "restart", "reload", "try-restart", "enable", "disable", "enable --now", "disable --now",
                   "mask", "unmask", "reset-failed")
APT_ACTIONS = {"update": ["update"], "upgrade": ["-y", "upgrade"], "full-upgrade": ["-y", "full-upgrade"],
               "autoremove": ["-y", "autoremove", "--purge"], "clean": ["clean"], "fix": ["-y", "install", "-f"]}
POWER_ACTIONS = ("reboot", "poweroff", "halt", "suspend", "cancel")
SIGNALS = ("TERM", "KILL", "HUP", "INT", "STOP", "CONT", "USR1", "USR2", "QUIT")
READ_ONLY = re.compile(
    r"^\s*(ls|cat|head|tail|grep|find|df|du|free|uptime|uname|whoami|id|hostname|date|ip\s+(a|addr|r|route|link)|ss|lsblk|"
    r"lsusb|lspci|ps|systemctl\s+(status|is-active|is-enabled|list-units|list-timers)|journalctl|docker\s+(ps|images|logs)|"
    r"nproc|sensors|wc|stat|file|which|pwd|dpkg\s+-l|apt\s+list|lsb_release|timedatectl\s+status|hostnamectl)\b[^;&|><`$]*$")
ENV = {"DEBIAN_FRONTEND": "noninteractive", "APT_LISTCHANGES_FRONTEND": "none", "NEEDRESTART_MODE": "a", "LC_ALL": "C.UTF-8"}


def audit(action: str, detail: str) -> None:
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%S%z')} {action} {detail[:400]!r}\n"
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    if AUDIT.exists() and AUDIT.stat().st_size > AUDIT_CAP:
        AUDIT.replace(AUDIT.with_suffix(".log.1"))
    fd = os.open(AUDIT, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as handle:
        handle.write(line)
    store.event("WARN", f"Agente Debian: {action} {detail[:160]}", "experts")


async def run(cmd: list[str], timeout: float = 120, cwd: str | None = None, stdin_null: bool = True) -> str:
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT, cwd=cwd, start_new_session=True,
            stdin=asyncio.subprocess.DEVNULL if stdin_null else None, env={**os.environ, **ENV})
    except FileNotFoundError:
        return f"codice di uscita 127\ncomando non trovato: {cmd[0]}"
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout)
    except asyncio.TimeoutError:
        os.killpg(proc.pid, signal.SIGKILL)
        await proc.wait()
        return f"codice di uscita 124\ntempo scaduto dopo {int(timeout)} s"
    text = out.decode("utf-8", "replace").strip()
    return f"codice di uscita {proc.returncode}\n{text[-OUT_TAIL:] or '(nessun output)'}"


def packages(value: str) -> list[str]:
    names = [item for item in re.split(r"[\s,]+", str(value or "").strip()) if item]
    if not names or len(names) > 30 or any(not PACKAGE_RE.fullmatch(name) or name.startswith("-") for name in names):
        raise ValueError("elenco pacchetti non valido (da 1 a 30 nomi apt)")
    return names


def unit_name(value: str) -> str:
    name = str(value or "").strip()
    if not UNIT_RE.fullmatch(name) or name.startswith("-"):
        raise ValueError("nome del servizio non valido")
    return name


def check_apt(args: dict) -> None:
    if "packages" in args:
        packages(args["packages"])
    if "action" in args and args["action"] not in APT_ACTIONS:
        raise ValueError(f"azione apt non valida: usa {', '.join(APT_ACTIONS)}")


def check_service(args: dict) -> None:
    unit_name(args.get("unit"))
    if args.get("action") not in SERVICE_ACTIONS:
        raise ValueError(f"azione non valida: usa {', '.join(SERVICE_ACTIONS)}")


def check_power(args: dict) -> None:
    if args.get("action") not in POWER_ACTIONS:
        raise ValueError(f"azione non valida: usa {', '.join(POWER_ACTIONS)}")


def check_ssh(args: dict) -> None:
    if not HOST_RE.fullmatch(str(args.get("host") or "")):
        raise ValueError("indirizzo del computer non valido")
    if not USER_RE.fullmatch(str(args.get("user") or "root")):
        raise ValueError("utente non valido")
    port = int(args.get("port") or 22)
    if not 1 <= port <= 65535:
        raise ValueError("porta non valida")
    if not str(args.get("command") or "").strip():
        raise ValueError("comando vuoto")


def check_path(args: dict) -> None:
    path = str(args.get("path") or "")
    if not path.startswith("/") or "\0" in path or ".." in Path(path).parts:
        raise ValueError("serve un percorso assoluto senza «..»")


def risky(args: dict) -> bool:
    return not READ_ONLY.match(str(args.get("command", "")))


async def apt_install(names: str, remove: bool = False, purge: bool = False) -> str:
    items = packages(names)
    verb = "purge" if remove and purge else ("remove" if remove else "install")
    audit(f"apt {verb}", " ".join(items))
    flags = ["-y", "-o", "Dpkg::Options::=--force-confold", "-o", "Dpkg::Options::=--force-confdef"]
    return await run(["apt-get", *flags, verb, "--", *items], timeout=1800)


async def apt_maintain(action: str) -> str:
    check_apt({"action": action})
    audit("apt", action)
    return await run(["apt-get", "-o", "Dpkg::Options::=--force-confold", *APT_ACTIONS[action]], timeout=3600)


async def apt_find(query: str) -> str:
    term = str(query or "").strip()
    if not term or term.startswith("-") or len(term) > 80:
        raise ValueError("ricerca non valida")
    return await run(["apt-cache", "search", "--", term], timeout=30)


async def service(unit: str, action: str) -> str:
    check_service({"unit": unit, "action": action})
    audit("systemctl", f"{action} {unit}")
    return await run(["systemctl", *action.split(), "--", unit_name(unit)], timeout=120)


async def power(action: str, minutes: int = 1) -> str:
    check_power({"action": action})
    when = max(1, min(1440, int(minutes or 1)))
    audit("power", f"{action} tra {when} min")
    if action == "cancel":
        return await run(["shutdown", "-c"], timeout=20)
    if action == "suspend":
        return await run(["systemctl", "suspend"], timeout=20)
    flag = {"reboot": "-r", "poweroff": "-P", "halt": "-H"}[action]
    return await run(["shutdown", flag, f"+{when}", "avviato dall'agente Debian"], timeout=20)


def ssh_key() -> Path:
    SSH_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    key = SSH_DIR / "id_ed25519"
    if not key.exists():
        import subprocess
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "nuxiva", "-f", str(key)], check=True, timeout=30)
    return key


async def ssh_public_key() -> str:
    if not shutil.which("ssh-keygen"):
        return "ssh-keygen non disponibile: installa openssh-client"
    key = await asyncio.to_thread(ssh_key)
    return f"{key.with_suffix('.pub').read_text(encoding='utf-8').strip()}\n(da aggiungere a ~/.ssh/authorized_keys del computer da raggiungere)"


async def ssh(host: str, command: str, user: str = "root", port: int = 22, timeout: int = 120) -> str:
    check_ssh({"host": host, "command": command, "user": user, "port": port})
    if not shutil.which("ssh"):
        return "ssh non disponibile: installa openssh-client"
    key = await asyncio.to_thread(ssh_key)
    audit("ssh", f"{user}@{host}:{port} {command}")
    options = ["-i", str(key), "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes", "-o", "ConnectTimeout=10",
               "-o", "StrictHostKeyChecking=accept-new", "-o", f"UserKnownHostsFile={SSH_DIR / 'known_hosts'}",
               "-o", "ServerAliveInterval=15", "-p", str(int(port))]
    return await run(["ssh", *options, "-l", user or "root", "--", host, command], timeout=max(10, min(1800, int(timeout))))


async def shell(command: str, timeout: int = 300, workdir: str = "") -> str:
    if not str(command or "").strip():
        raise ValueError("comando vuoto")
    cwd = workdir if workdir and Path(workdir).is_dir() else "/root" if Path("/root").is_dir() else "/"
    audit("shell", command)
    return await run(["bash", "-lc", command], timeout=max(5, min(3600, int(timeout))), cwd=cwd)


def read_file(path: str, limit: int = 20000) -> str:
    check_path({"path": path})
    target = Path(path)
    if not target.is_file():
        raise ValueError("file non trovato")
    with target.open("rb") as handle:
        data = handle.read(max(1, min(100000, int(limit))))
    return data.decode("utf-8", "replace")


def write_file(path: str, content: str, mode: str = "") -> str:
    check_path({"path": path})
    target = Path(path)
    audit("write_file", path)
    target.parent.mkdir(parents=True, exist_ok=True)
    previous = target.stat() if target.exists() else None
    if previous:
        backup = target.with_name(f"{target.name}.nuxiva-{int(time.time())}.bak")
        shutil.copy2(target, backup)
    temporary = target.with_name(f".{target.name}.nuxiva.tmp")
    temporary.write_text(str(content), encoding="utf-8")
    if mode and re.fullmatch(r"[0-7]{3,4}", mode):
        os.chmod(temporary, int(mode, 8))
    elif previous:
        os.chmod(temporary, previous.st_mode & 0o7777)
        os.chown(temporary, previous.st_uid, previous.st_gid)
    os.replace(temporary, target)
    return f"scritto {path} ({len(str(content))} caratteri)" + (f", copia precedente in {backup.name}" if previous else "")


async def processes(sort: str = "cpu", limit: int = 15) -> str:
    key = "-%mem" if sort == "mem" else "-%cpu"
    count = max(1, min(60, int(limit or 15)))
    out = await run(["ps", "-eo", "pid,ppid,user,%cpu,%mem,etime,stat,comm", f"--sort={key}"], timeout=15)
    head, _, body = out.partition("\n")
    return head + "\n" + "\n".join(body.splitlines()[:count + 1])


async def kill(pid: int, sig: str = "TERM") -> str:
    number = int(pid)
    if number <= 1 or number == os.getpid():
        raise ValueError("processo protetto: per i servizi usa service_control")
    if sig not in SIGNALS:
        raise ValueError(f"segnale non valido: usa {', '.join(SIGNALS)}")
    audit("kill", f"{sig} {number}")
    return await run(["kill", f"-{sig}", str(number)], timeout=10)


async def network() -> str:
    parts = []
    for title, cmd in (("interfacce", ["ip", "-br", "addr"]), ("rotte", ["ip", "route"]), ("porte in ascolto", ["ss", "-tulpn"])):
        parts.append(f"## {title}\n{(await run(cmd, timeout=15)).split(chr(10), 1)[-1]}")
    return "\n".join(parts)
