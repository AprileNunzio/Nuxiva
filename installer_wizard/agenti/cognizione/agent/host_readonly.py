import asyncio
import os
import re
import shlex
from pathlib import Path

from agenti.agent.paths import FILES

MAX_ARGS = 24
MAX_OUTPUT = 20_000
TIMEOUT = 60.0
FORBIDDEN_CHARS = re.compile(r"[;&|<>`$\\\n\r\0(){}?~!]")
BLOCKED_PREFIXES = ("/etc/nuxiva", "/var/lib/nuxiva", "/etc/shadow", "/etc/gshadow", "/etc/sudoers", "/etc/ssh", "/root",
                    "/run/nuxiva", "/proc/kcore")
BLOCKED_PARTS = {".ssh", ".gnupg", ".aws", ".kube"}
BLOCKED_NAMES = re.compile(r"^(\.env.*|.*\.(pem|key|p12|pfx)|id_(rsa|ed25519|ecdsa|dsa)|nuxiva\.env)$")
FIND_DENIED = {"-files0-from", "-exec", "-execdir", "-ok", "-okdir", "-delete", "-fprint", "-fprint0", "-fprintf", "-fls"}
JOURNAL_DENIED = ("--vacuum", "--rotate", "--flush", "--sync", "--setup-keys", "--relinquish", "--smart-relinquish",
                  "--update-catalog", "--follow", "-f")
ENV = {"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C.UTF-8", "HOME": "/nonexistent"}
FILE_TOOLS = {"ls", "cat", "head", "tail", "grep", "wc", "stat", "file", "du", "find"}
PLAIN = {"df", "free", "uptime", "uname", "whoami", "id", "lsblk", "lsusb", "lspci", "nproc", "pwd", "which", "ps", "ss",
         "lsb_release", "hostnamectl", "echo"}


def path_blocked(arg: str) -> bool:
    resolved = Path(os.path.realpath(os.path.join(str(FILES), arg)))
    text = str(resolved)
    if any(text == p or text.startswith(p + "/") for p in BLOCKED_PREFIXES):
        return True
    if text.startswith("/proc/") and (text.endswith("/environ") or "/environ" in text):
        return True
    parts = set(resolved.parts)
    return bool(parts & BLOCKED_PARTS) or bool(BLOCKED_NAMES.match(resolved.name))


def _flags(args: list[str]) -> list[str]:
    return [a for a in args if a.startswith("-")]


FILE_FLAG_PREFIXES = ("--file", "--files0-from", "--exclude-from", "--magic-file", "--follow", "--output")


def _files_ok(cmd: str, args: list[str]) -> bool:
    if cmd == "find" and FIND_DENIED & set(args):
        return False
    if cmd != "find" and any(a.startswith(FILE_FLAG_PREFIXES) for a in args):
        return False
    if cmd in ("grep", "file", "stat", "du", "wc") and any(a in ("-f", "-X", "-m") for a in args) and cmd != "stat":
        return False
    if cmd == "tail" and any(a in ("-f", "-F") for a in args):
        return False
    return not any(path_blocked(a) for a in args if not a.startswith("-") or cmd == "find" and "/" in a)


def _ip_ok(args: list[str]) -> bool:
    if not args or args[0] not in ("a", "addr", "address", "r", "route", "link"):
        return False
    return all(a in ("show", "list", "get", "-s", "-4", "-6", "-br", "-brief") or re.fullmatch(r"[A-Za-z0-9_.:/-]{1,40}", a)
               for a in args[1:]) and not {"add", "del", "delete", "flush", "set", "change", "replace"} & set(args)


def _systemctl_ok(args: list[str]) -> bool:
    verbs = [a for a in args if not a.startswith("-")]
    return bool(verbs) and verbs[0] in ("status", "is-active", "is-enabled", "list-units", "list-timers") and \
        all(a in ("--no-pager", "--failed", "--all", "-a", "-l", "--full", "-n") or not a.startswith("-") or a.startswith("--type=")
            for a in args)


def _docker_ok(args: list[str]) -> bool:
    return bool(args) and args[0] in ("ps", "images", "logs") and not {"-f", "--follow"} & set(args)


def _ping_ok(args: list[str]) -> bool:
    return len(args) == 3 and args[0] == "-c" and args[1].isdigit() and 1 <= int(args[1]) <= 10 and \
        re.fullmatch(r"[A-Za-z0-9.-]{1,253}", args[2]) is not None


def _top_ok(args: list[str]) -> bool:
    return args == ["-bn1"]


def _ollama_ok(args: list[str]) -> bool:
    return args in (["list"], ["ps"])


def _date_ok(args: list[str]) -> bool:
    return all(a.startswith("+") or a in ("-u", "--utc", "-I", "--iso-8601") for a in args)


def _sensors_ok(args: list[str]) -> bool:
    return not {"-s", "--set"} & set(args)


def _hostnamectl_ok(args: list[str]) -> bool:
    return args in ([], ["status"])


def _lsb_ok(args: list[str]) -> bool:
    return all(a in ("-a", "-d", "-r", "-c", "-i", "-s") for a in args)


PKG_NAME = re.compile(r"[A-Za-z0-9.+*:_-]{1,80}")
APT_FLAGS = ("--installed", "--upgradable")
DPKG_VERBS = ("-l", "--list", "-s", "--status", "-L")


def _pkg_ok(cmd: str, args: list[str]) -> bool:
    if not args:
        return False
    verb, rest = args[0], args[1:]
    if cmd == "dpkg":
        return verb in DPKG_VERBS and all(PKG_NAME.fullmatch(a) for a in rest)
    return verb == "list" and all(a in APT_FLAGS or PKG_NAME.fullmatch(a) for a in rest)


SPECIAL = {"ip": _ip_ok, "systemctl": _systemctl_ok, "docker": _docker_ok, "ping": _ping_ok, "top": _top_ok,
           "ollama": _ollama_ok, "date": _date_ok, "sensors": _sensors_ok, "hostnamectl": _hostnamectl_ok,
           "lsb_release": _lsb_ok, "hostname": lambda a: not a, "timedatectl": lambda a: a in ([], ["status"])}


def _journal_ok(args: list[str]) -> bool:
    return not any(a == d or (d.startswith("--") and a.startswith(d)) for a in args for d in JOURNAL_DENIED)


def parse(command: str) -> list[str] | None:
    if not isinstance(command, str) or not command.strip() or len(command) > 400 or FORBIDDEN_CHARS.search(command):
        return None
    try:
        argv = shlex.split(command, posix=True)
    except ValueError:
        return None
    if not argv or len(argv) > MAX_ARGS:
        return None
    cmd, args = argv[0], argv[1:]
    if cmd in FILE_TOOLS:
        return argv if _files_ok(cmd, args) else None
    if cmd == "journalctl":
        return argv if _journal_ok(args) else None
    if cmd in ("dpkg", "apt"):
        return argv if _pkg_ok(cmd, args) else None
    if cmd in SPECIAL:
        return argv if SPECIAL[cmd](args) else None
    if cmd in PLAIN:
        return argv if not any(a.startswith("-") and a in ("--help-all",) for a in args) else None
    return None


async def run(argv: list[str]) -> tuple[int, str]:
    FILES.mkdir(parents=True, exist_ok=True)
    try:
        proc = await asyncio.create_subprocess_exec(*argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
                                                    env=ENV, cwd=str(FILES), stdin=asyncio.subprocess.DEVNULL)
    except FileNotFoundError:
        return 127, f"comando non trovato: {argv[0]}"
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), TIMEOUT)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return 124, "tempo scaduto"
    return proc.returncode or 0, out[:MAX_OUTPUT].decode("utf-8", "replace").strip()
