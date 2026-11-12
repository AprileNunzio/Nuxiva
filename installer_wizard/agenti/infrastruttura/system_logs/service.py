"""Read-only log discovery, normalization, redaction and portable export."""
import csv
import hashlib
import io
import json
import re
import shutil
import socket
import time
import platform
import psutil
from datetime import datetime, timezone
from pathlib import Path

from config import LOG_DIR
from health import sh
from state import AUDIT_FILE, store

_SECRET = re.compile(r'''(?i)(\b[A-Za-z0-9_-]*(?:password|passwd|secret|token|api[_-]?key|authorization|cookie|nuxiva_session)[A-Za-z0-9_-]*\b["']?\s*[:=]\s*)(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|(?:Bearer\s+)?[^\s,;"']+)''')
_AUTH_HEADER = re.compile(r'''(?i)(\b[A-Za-z0-9_-]*(?:authorization|cookie)[A-Za-z0-9_-]*\b["']?\s*[:=]\s*)(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[^\r\n]+)''')
_BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
_URL_PASSWORD = re.compile(r"(https?://[^\s/:]+:)[^\s/@]+(@)")
_LEVEL = re.compile(r"\b(ERROR|CRITICAL|FATAL|WARNING|WARN|DEBUG|INFO|NOTICE|TRACEBACK)\b", re.I)
_EXCEPTION = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*(?:Error|Exception):")
_TIME_PREFIX = re.compile(r"^\d{4}-\d\d-\d\d[T ]\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)?")
MAX_LINES = 3000
_catalog_cache: dict[str, tuple[float, dict]] = {}


def redact(text: str) -> str:
    value = _AUTH_HEADER.sub(lambda match: match[1] + "[REDACTED]", str(text))
    value = _SECRET.sub(lambda match: match[1] + "[REDACTED]", value)
    value = _BEARER.sub("Bearer [REDACTED]", value)
    value = re.sub(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b", "[REDACTED]", value)
    value = re.sub(r"\bv1\.local\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b|\bjv_[A-Za-z0-9_-]{32,}\b", "[REDACTED]", value)
    return _URL_PASSWORD.sub(r"\1[REDACTED]\2", value)


def local_node_id() -> str | None:
    try:
        from server.features.mesh_coordinator.p2p_mesh import p2p_mesh
        return p2p_mesh.node_id
    except (ImportError, AttributeError):
        return None


def is_local(node_id: str) -> bool:
    return node_id == "local" or node_id == local_node_id()


async def discover(node_id: str = "local") -> dict:
    cached = _catalog_cache.get(node_id)
    if cached and time.monotonic() - cached[0] < 15:
        return cached[1]
    local = is_local(node_id)
    sources = [{"id": "events", "kind": "events", "name": "Nuxiva", "available": True}]
    warnings = []
    if local:
        if shutil.which("journalctl"):
            sources.append({"id": "journal", "kind": "journal", "name": "System journal", "available": True})
            code, output = await sh("systemctl", "list-units", "--all", "--type=service", "--output=json", "--no-pager", timeout=8)
            try:
                units = json.loads(output) if code == 0 else []
            except ValueError:
                units = []
            if code != 0:
                warnings.append("service_discovery_unavailable")
            for unit in units:
                name = unit.get("unit", "")
                if re.fullmatch(r"[A-Za-z0-9_.:@\\-]+\.service", name):
                    sources.append({"id": f"unit:{name}", "kind": "unit", "name": name, "available": True, "state": unit.get("active"), "description": unit.get("description", "")})
        if shutil.which("docker"):
            code, output = await sh("docker", "ps", "-a", "--format", "{{json .}}", timeout=8)
            if code:
                warnings.append("container_discovery_unavailable")
            else:
                for line in output.splitlines():
                    try:
                        container = json.loads(line)
                    except ValueError:
                        continue
                    name = container.get("Names", "")
                    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", name):
                        sources.append({"id": f"container:{name}", "kind": "container", "name": name, "available": True, "state": container.get("State")})
        root = Path(LOG_DIR).resolve()
        for path in sorted(root.rglob("*.log"))[:200]:
            resolved = path.resolve()
            if resolved.is_relative_to(root) and resolved.is_file():
                sources.append({"id": "file:" + hashlib.sha256(str(resolved).encode()).hexdigest()[:16], "kind": "file", "name": str(path.relative_to(root)), "available": True, "_path": str(resolved)})
    result = {"sources": sources, "warnings": warnings, "node_id": node_id, "local_node_id": local_node_id(), "hostname": socket.gethostname(), "scope": "local" if local else "server_events_only", "remote_logs_supported": local}
    if len(_catalog_cache) >= 64:
        _catalog_cache.pop(next(iter(_catalog_cache)))
    _catalog_cache[node_id] = (time.monotonic(), result)
    return result


def timestamp(value) -> float | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError):
        return None


def tail_file(path: Path, limit: int, max_bytes: int = 4 * 1024 * 1024) -> list[str]:
    with path.open("rb") as stream:
        stream.seek(0, 2)
        start = max(0, stream.tell() - max_bytes)
        stream.seek(start)
        lines = stream.read(max_bytes).decode("utf-8", "replace").splitlines()
    if start and lines:
        lines = lines[1:]
    return lines[-limit:]


def normalize(message: str, source: str, at: float | None = None, priority=None, level: str = "") -> dict:
    severity = "info"
    provenance = "inferred"
    try:
        number = int(priority)
        severity = "error" if number <= 3 else "warning" if number == 4 else "debug" if number >= 7 else "info"
        provenance = "journal"
    except (ValueError, TypeError):
        match = _LEVEL.search(level or message)
        if match:
            name = match[1].upper()
            severity = "error" if name in ("ERROR", "CRITICAL", "FATAL", "TRACEBACK") else "warning" if name in ("WARNING", "WARN") else "debug" if name == "DEBUG" else "info"
            provenance = "declared" if level else "inferred"
        elif _EXCEPTION.search(message):
            severity = "error"
    return {"timestamp": at, "source": redact(source), "severity": severity, "severity_source": provenance, "message": redact(message[:12000])}


async def entries(source_id: str, node_id: str, minutes: int, limit: int, severity: str, query: str) -> dict:
    catalog = await discover(node_id)
    source = next((item for item in catalog["sources"] if item["id"] == source_id), None)
    if not source:
        raise KeyError("source_not_available_for_device")
    start = time.time() - minutes * 60
    rows = []
    code = 0
    output = ""
    scanned = 0
    if source["kind"] == "events":
        # Persistent audit file survives supervisor restarts. Keep reads bounded.
        if Path(AUDIT_FILE).is_file():
            raw = []
            for line in tail_file(Path(AUDIT_FILE), limit):
                try:
                    raw.append(json.loads(line))
                except ValueError:
                    continue
        else:
            raw = list(store.events)[-limit:]
        scanned = len(raw)
        for event in raw:
            if not isinstance(event, dict):
                continue
            message = str(event.get("msg", ""))
            if catalog["scope"] != "local" and event.get("node_id") != node_id:
                continue
            rows.append(normalize(message, str(event.get("component", "Nuxiva")), timestamp(event.get("ts")), level=str(event.get("level", ""))))
    elif source["kind"] in ("journal", "unit"):
        args = ["journalctl", "--output=json", "--no-pager", "--since", f"-{minutes} minutes", "--lines", str(limit)]
        if source["kind"] == "unit":
            args.extend(["--unit", source_id.removeprefix("unit:")])
        code, output = await sh(*args, timeout=8)
        for line in output.splitlines():
            try:
                event = json.loads(line)
                at = int(event.get("__REALTIME_TIMESTAMP", 0)) / 1_000_000 or None
                rows.append(normalize(str(event.get("MESSAGE", "")), str(event.get("_SYSTEMD_UNIT") or event.get("SYSLOG_IDENTIFIER") or source_id), at, event.get("PRIORITY")))
            except (ValueError, TypeError, AttributeError):
                continue
    else:
        if source["kind"] == "container":
            code, output = await sh("docker", "logs", "--timestamps", "--since", f"{minutes}m", "--tail", str(limit), source_id.removeprefix("container:"), timeout=8)
            lines = output.splitlines()
        else:
            path = Path(source["_path"]).resolve()
            if not path.is_relative_to(Path(LOG_DIR).resolve()):
                raise KeyError("source_not_available_for_device")
            lines = tail_file(path, limit)
        for line in lines:
            prefix = _TIME_PREFIX.match(line)
            at = timestamp(prefix[0]) if prefix else None
            rows.append(normalize(line, source["name"], at))
    if code:
        raise RuntimeError(redact(output[-1000:]) or "source_unavailable")
    sampled = len(rows)
    scanned = max(scanned, sampled)
    rows = [row for row in rows if (row["timestamp"] is None or row["timestamp"] >= start) and (severity == "all" or row["severity"] == severity) and query.casefold() in row["message"].casefold()]
    rows = rows[-limit:]
    for index, row in enumerate(rows):
        row["id"] = hashlib.sha256(f"{row['timestamp']}:{row['source']}:{row['message']}:{index}".encode()).hexdigest()[:20]
    patterns = {"python_dependency_missing": "ModuleNotFoundError", "dns_failure": "Could not resolve", "permission_denied": "Permission denied", "connection_refused": "Connection refused"}
    analysis = [{"code": key, "occurrences": sum(pattern.casefold() in row["message"].casefold() for row in rows)} for key, pattern in patterns.items()]
    return {"entries": rows, "counts": {level: sum(row["severity"] == level for row in rows) for level in ("error", "warning", "info", "debug")}, "analysis": [item for item in analysis if item["occurrences"]], "sampled": sampled, "scanned": scanned, "untimed_count": sum(row["timestamp"] is None for row in rows), "limit_reached": scanned >= limit, "source": source_id, "node_id": node_id, "scope": catalog["scope"], "phase": store.phase if catalog["scope"] == "local" else None, "collector_hostname": socket.gethostname(), "generated_at": datetime.now(timezone.utc).isoformat(), "filters": {"minutes": minutes, "severity": severity, "query": redact(query)}, "warnings": catalog["warnings"], "redacted": True}


async def diagnostics(payload: dict) -> dict:
    catalog = await discover(payload["node_id"])
    machine = None
    warnings = list(payload.get("warnings", []))
    if catalog["scope"] == "local":
        machine = {"hostname": socket.gethostname(), "system": platform.system(), "release": platform.release(),
                   "architecture": platform.machine(), "python": platform.python_version(),
                   "collected_at": datetime.now(timezone.utc).isoformat()}
        try:
            memory, disk = psutil.virtual_memory(), psutil.disk_usage("/")
            machine.update({"logical_cpus": psutil.cpu_count(), "boot_time": psutil.boot_time(),
                            "memory": {"total": memory.total, "available": memory.available},
                            "disk": {"total": disk.total, "free": disk.free}})
        except OSError:
            warnings.append("hardware_snapshot_unavailable")
    inventory = [{key: redact(value) if isinstance(value, str) and key != "id" else value for key, value in source.items() if not key.startswith("_")}
                 for source in catalog["sources"]]
    return {**payload, "report_type": "nuxiva.diagnostics", "schema_version": 1, "machine": machine,
            "sources": inventory, "warnings": warnings,
            "limitations": ["bounded_sample", "recognizable_secrets_only"] + (["remote_logs_not_exposed"] if machine is None else [])}


def export(payload: dict, format: str) -> tuple[str, str]:
    if format in ("json", "report"):
        return json.dumps(payload, ensure_ascii=False, indent=2), "application/json"
    if format == "txt":
        return "\n".join(f"{row['timestamp'] or '-'} [{row['severity'].upper()}] [{row['source']}] {row['message']}" for row in payload["entries"]), "text/plain; charset=utf-8"
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    fields = ("timestamp", "severity", "source", "message")
    writer.writerow(fields)
    for row in payload["entries"]:
        values = [str(row.get(field) or "") for field in fields]
        writer.writerow(["'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value for value in values])
    return buffer.getvalue(), "text/csv; charset=utf-8"
