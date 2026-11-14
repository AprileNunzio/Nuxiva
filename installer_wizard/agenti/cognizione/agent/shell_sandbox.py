import logging
import os

log = logging.getLogger("nuxiva.agent.sandbox")

MODES = ("sandbox", "host")
OUTPUT_TAIL = 5000
_gateway = None


def mode() -> str:
    value = os.environ.get("NUXIVA_RUN_COMMAND", "sandbox").strip().lower()
    return value if value in MODES else "sandbox"


def _build():
    from sandbox_broker.config import BrokerConfig
    from sandbox_broker.secret import secret_provider
    from server.features.sandbox.application.gateway import SandboxGateway
    from server.features.sandbox.infrastructure.broker_client import BrokerClient
    config = BrokerConfig.from_env()
    return SandboxGateway(BrokerClient(config.socket_path, secret_provider(config.env_file)))


def gateway():
    global _gateway
    if _gateway is None:
        _gateway = _build()
    return _gateway


def format_report(report) -> str:
    text = "\n".join(part for part in (report.stdout, report.stderr) if part)[-OUTPUT_TAIL:]
    note = ""
    if report.timed_out:
        note = "\n[tempo scaduto nel sandbox]"
    elif report.oom_killed:
        note = "\n[memoria del sandbox esaurita]"
    return f"codice di uscita {report.exit_code} (sandbox {report.backend})\n{text}{note}"


async def run(command: str, wall_seconds: int = 120) -> str:
    from server.features.sandbox.domain.errors import SandboxError
    from server.features.sandbox.domain.spec import ResourceLimits
    limits = ResourceLimits(memory_mb=256, cpus=1.0, pids=64, wall_seconds=wall_seconds, output_bytes=256 * 1024)
    try:
        report = await gateway().run_bash(command, limits=limits)
    except SandboxError as exc:
        log.error("Esecuzione nel sandbox rifiutata: %s", exc)
        raise RuntimeError(f"sandbox non disponibile, comando non eseguito: {exc}") from exc
    return format_report(report)
