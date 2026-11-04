from __future__ import annotations

import logging
from collections.abc import Callable

from features.activation.domain.telemetry import TelemetryParser, TelemetrySnapshot

log = logging.getLogger("nuxiva.activation.step_runner")


class StepRunner:
    def __init__(self, run_action_fn: Callable) -> None:
        self._run_action = run_action_fn

    async def execute_step(
        self,
        step_id: str,
        action: str,
        on_telemetry: Callable[[TelemetrySnapshot], None] | None = None,
    ) -> tuple[int, str]:
        elapsed = 0.0
        snapshot = TelemetrySnapshot()

        def stream_line(line: str) -> None:
            nonlocal snapshot
            parsed = TelemetryParser.parse_line(line)
            if parsed and on_telemetry:
                snapshot = TelemetrySnapshot(
                    progress=float(parsed.get("progress", snapshot.progress)),
                    speed=str(parsed.get("speed", snapshot.speed)),
                    detail=str(parsed.get("detail", snapshot.detail)),
                    message=str(parsed.get("message", snapshot.message)),
                    elapsed=elapsed,
                )
                on_telemetry(snapshot)

        code, error = await self._run_action(step_id, action, stream_line)
        return code, error
