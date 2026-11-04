from __future__ import annotations

import logging
from typing import Any

from config import write_env
from features.activation.domain.errors import JourneyError

log = logging.getLogger("nuxiva.activation.configure_handler")


class ConfigureStepHandler:
    @staticmethod
    def handle_step(sequence_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        if sequence_id == "assistant_naming":
            name = str(payload.get("name", "NUXIVA")).strip().upper()[:32]
            if not name:
                raise JourneyError("activation.invalid_assistant_name")
            write_env({"NUXIVA_ASSISTANT_NAME": name})
            return {"name": name}

        if sequence_id == "assistant_voice":
            gender = str(payload.get("gender", "female")).strip().lower()
            if gender not in ("female", "male"):
                raise JourneyError("activation.invalid_assistant_gender")
            write_env({"NUXIVA_ASSISTANT_GENDER": gender})
            return {"gender": gender}

        if sequence_id == "owner_identity":
            first_name = str(payload.get("first_name", "")).strip()[:48]
            last_name = str(payload.get("last_name", "")).strip()[:48]
            if not first_name:
                raise JourneyError("activation.invalid_owner_name")
            write_env({
                "NUXIVA_OWNER_FIRST": first_name,
                "NUXIVA_OWNER_LAST": last_name,
            })
            return {"first_name": first_name, "last_name": last_name}

        if sequence_id == "mcp_gate":
            enabled = bool(payload.get("enabled", True))
            write_env({"NUXIVA_MCP_ENABLED": "1" if enabled else "0"})
            return {"enabled": enabled}

        return {"ok": True}
