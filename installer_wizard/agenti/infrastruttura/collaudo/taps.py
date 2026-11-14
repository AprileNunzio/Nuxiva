import asyncio
import json
import logging
import re
import shutil

from agenti.collaudo import emit

PRIORITY = {"0": "error", "1": "error", "2": "error", "3": "error", "4": "warn"}
SERVICE_PREFIX = "nuxiva-"
SKIP_LOGGERS = ("nuxiva.collaudo",)
DOMAIN_BY_PREFIX = (("nuxiva.ear", "ear"), ("nuxiva.vision", "vision"), ("nuxiva.sentinel", "sentinel"),
                    ("nuxiva.mcp", "mcp"), ("nuxiva.loops", "supervisor"), ("nuxiva.supervisor", "supervisor"))
TOPIC_DOMAINS = (("sentinel.", "sentinel"), ("ear.", "ear"), ("voice.", "ear"), ("vision.", "vision"), ("camera", "vision"),
                 ("mcp.", "mcp"), ("agent.", "worker"), ("worker.", "worker"), ("task", "worker"), ("system.", "supervisor"))
TOPIC_UNSAFE = re.compile(r"[^a-z0-9_.:-]")
SAFE_FIELDS = 12
NOISY = ("synapse.", "ui.", "collaudo.")


def _domain(name: str) -> str:
    for prefix, domain in DOMAIN_BY_PREFIX:
        if name.startswith(prefix):
            return domain
    return "error"


class LogTap(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)

    def emit(self, record: logging.LogRecord) -> None:
        if record.name.startswith(SKIP_LOGGERS):
            return
        try:
            level = "error" if record.levelno >= logging.ERROR else "warn"
            fields = {"logger": record.name.lower()[:32].replace(" ", "_"), "msg": record.getMessage()[:400]}
            if record.exc_info and record.exc_info[0] is not None:
                fields["exc"] = record.exc_info[0].__name__.lower()
            emit.emit("error" if level == "error" else _domain(record.name), level, "log", src="supervisor", **fields)
        except (ValueError, TypeError, OSError):
            return


def install_log_tap() -> LogTap:
    handler = LogTap()
    logging.getLogger().addHandler(handler)
    return handler


def bus_event(envelope) -> None:
    topic = envelope.topic
    if topic.startswith(NOISY):
        return
    domain = next((d for p, d in TOPIC_DOMAINS if topic.startswith(p) or p in topic), "supervisor")
    kind = TOPIC_UNSAFE.sub("_", topic.lower())[:64]
    fields = {}
    for key, value in list(envelope.payload.items())[:SAFE_FIELDS]:
        if isinstance(value, (bool, int, float)):
            fields[str(key)] = value
        elif isinstance(value, str) and len(value) <= 64:
            fields[str(key)] = value
    emit.emit(domain, "info", kind, src=(envelope.origin or "bus")[:48], **fields)


def install_bus_tap(bus):
    return bus.subscribe(">", bus_event)


def sentinel_event(event: dict) -> None:
    subject = event.get("subject") or {}
    emit.emit("sentinel", "info", str(event.get("kind", "event")), src="sentinel", corr=None,
              subject_type=str(subject.get("type", "")), subject_ref=str(subject.get("id", "")),
              place=str(event.get("place") or ""), key=str(event.get("narrative", {}).get("key", "")),
              sensitivity=str(event.get("sensitivity", "")), origin=str(event.get("source", "")),
              params_n=len(event.get("narrative", {}).get("params", {})))


async def journal_tail(stop: asyncio.Event) -> None:
    binary = shutil.which("journalctl")
    if binary is None:
        return
    process = await asyncio.create_subprocess_exec(
        binary, "-f", "-n", "0", "-o", "json", "-p", "warning", "--no-pager", "-u", f"{SERVICE_PREFIX}*",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    try:
        assert process.stdout is not None
        while not stop.is_set():
            line = await process.stdout.readline()
            if not line:
                break
            try:
                row = json.loads(line)
            except ValueError:
                continue
            unit = str(row.get("_SYSTEMD_UNIT", "")).removesuffix(".service")
            emit.emit("error", PRIORITY.get(str(row.get("PRIORITY", "4")), "warn"), "journal", src="journald",
                      unit=unit[:32].lower(), msg=str(row.get("MESSAGE", ""))[:400])
    finally:
        if process.returncode is None:
            process.terminate()
            await process.wait()
