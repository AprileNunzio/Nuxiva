import re
import time
from dataclasses import dataclass, field
from typing import Any

from agenti.agency import project_room
from agenti.agency.project_scaffolder import project_scaffolder
from agenti.agency.scanner import tool_scanner


@dataclass
class PendingCallback:
    capability_name: str
    person_slug: str
    channel: str
    registered_at: float
    user_prompt: str
    status: str = "forging"
    ready_message: str = ""
    widget: dict[str, Any] = field(default_factory=dict)


class OnDemandCapabilityGovernor:
    def __init__(self) -> None:
        self.pending_callbacks: dict[str, list[PendingCallback]] = {}
        self.forged_registry: dict[str, dict[str, Any]] = {}

    def _clean_name(self, query: str) -> str:
        q = query.lower().strip()
        q = re.sub(r"[\?!.,;:\"']+", "", q)
        q = re.sub(r"^(nuxiva|hey nuxiva|ciao nuxiva)\s+", "", q).strip()
        q = re.sub(r"^(vogliamo giocare a|voglio giocare a|giochiamo a|giocare a|gioco della|gioco del|gioco di|apri|crea|avvia)\s+", "", q).strip()
        return q.replace(" ", "_")[:60] or "generic_capability"

    def check_capability_available(self, capability_name: str) -> bool:
        clean = self._clean_name(capability_name)
        if clean in self.forged_registry:
            return True
        tools = tool_scanner.scan_tools()
        if clean in tools or any(clean in k for k in tools):
            return True
        return False

    def request_capability(
        self,
        user_query: str,
        person_slug: str = "ospite",
        channel: str = "voice",
        lang: str = "it",
    ) -> dict[str, Any]:
        cap_name = self._clean_name(user_query)
        is_available = self.check_capability_available(cap_name)

        if is_available:
            return {
                "available": True,
                "capability": cap_name,
                "message": f"Il modulo «{cap_name}» è pronto all'uso. Avvio immediato in corso.",
                "action": "launch_directly",
            }

        proj_id = f"proj_forge_{cap_name}_{int(time.time() * 1000)}"
        prompt_title = f"Modulo Autonomo: {cap_name.replace('_', ' ').title()}"

        scaffold = project_scaffolder.scaffold_modular_architecture(
            project_name=cap_name,
            domain="on_demand_capability",
            capabilities=[cap_name, "state_sync", "ui_render"],
        )

        base_stub = {
            "id": proj_id,
            "title": prompt_title,
            "goal": f"Sviluppo completo e collaudo del modulo {cap_name} su richiesta di {person_slug}",
            "status": "planning",
            "scaffold": scaffold,
            "pair_programming": True,
        }
        ceo_stub = {"id": "ceo", "status": "planning"}
        shared_stub = {"rules_count": 1690, "reviews_count": 945}

        pair_agents = [
            {"id": "lead_frontend", "role": "tsx_expert", "seated": True, "status": "running"},
            {"id": "lead_backend", "role": "rust_expert", "seated": True, "status": "running"},
        ]

        project_room.build_project_room(
            {"project": base_stub, "pair_programming": True},
            base_stub,
            pair_agents,
            ceo_stub,
            shared_stub,
        )

        callback = PendingCallback(
            capability_name=cap_name,
            person_slug=person_slug,
            channel=channel,
            registered_at=time.time(),
            user_prompt=user_query,
            status="forging",
        )
        self.pending_callbacks.setdefault(cap_name, []).append(callback)

        display_cap = cap_name.replace("_", " ").title()
        spoken_response = (
            f"Non ho ancora il modulo «{display_cap}» in memoria. "
            "Ho avvisato il Direttore CEO di allestire la stanza di progetto e crearlo per noi. "
            "Vuoi che ti avvisi non appena è pronto per utilizzarlo insieme?"
        )

        return {
            "available": False,
            "capability": cap_name,
            "project_id": proj_id,
            "message": spoken_response,
            "action": "forging_in_background",
            "proactive_callback_hook": True,
        }

    def complete_forge(
        self,
        capability_name: str,
        artifact_data: dict[str, Any] | None = None,
        custom_ready_message: str = "",
    ) -> dict[str, Any]:
        cap_name = self._clean_name(capability_name)
        display_cap = cap_name.replace("_", " ").title()

        ready_msg = custom_ready_message or f"Il modulo «{display_cap}» è pronto e verificato! Possiamo iniziare subito."
        widget = {
            "id": f"widget_cap_{cap_name}",
            "type": "interactive_capability_surface",
            "title": display_cap,
            "style": "borderless_glassmorphic",
            "visual": {"border": "none", "background": "transparent", "glow": "cyan"},
            "payload": artifact_data or {},
        }

        self.forged_registry[cap_name] = {
            "capability": cap_name,
            "forged_at": time.time(),
            "widget": widget,
            "status": "ready",
        }

        callbacks = self.pending_callbacks.pop(cap_name, [])
        for cb in callbacks:
            cb.status = "ready"
            cb.ready_message = ready_msg
            cb.widget = widget

        return {
            "status": "published",
            "capability": cap_name,
            "notified_callbacks_count": len(callbacks),
            "ready_message": ready_msg,
            "widget": widget,
        }


on_demand_governor = OnDemandCapabilityGovernor()
