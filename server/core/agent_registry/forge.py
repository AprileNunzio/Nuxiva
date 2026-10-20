import os
import json
import time
from typing import Dict, List, Optional
from server.config.env import settings
from server.core.agent_registry.catalog import (
    AgentCapabilitySpec,
    DEFAULT_AGENT_CATALOG,
)

class CustomAgentForge:
    _instance = None

    def __new__(cls) -> "CustomAgentForge":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._custom_agents_dir = os.path.join(settings.DATA_DIR, "custom_agents")
            os.makedirs(cls._instance._custom_agents_dir, exist_ok=True)
            cls._instance._agents: Dict[str, AgentCapabilitySpec] = {}
            cls._instance._init_catalog()
        return cls._instance

    def _init_catalog(self) -> None:
        # Carica catalogo predefinito
        for agent_id, spec in DEFAULT_AGENT_CATALOG.items():
            self._agents[agent_id] = spec.model_copy()

        # Carica eventuali agenti custom creati dall'utente
        if os.path.exists(self._custom_agents_dir):
            for fname in os.listdir(self._custom_agents_dir):
                if fname.endswith(".json"):
                    fpath = os.path.join(self._custom_agents_dir, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            spec = AgentCapabilitySpec(**data)
                            self._agents[spec.id] = spec
                    except Exception:
                        pass

    def get_agent(self, agent_id: str) -> Optional[AgentCapabilitySpec]:
        return self._agents.get(agent_id)

    def list_all_agents(self) -> List[AgentCapabilitySpec]:
        return list(self._agents.values())

    def forge_custom_agent(self, spec: AgentCapabilitySpec) -> AgentCapabilitySpec:
        spec.is_custom = True
        spec.created_at = time.time()
        self._agents[spec.id] = spec

        fpath = os.path.join(self._custom_agents_dir, f"{spec.id}.json")
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(spec.model_dump(), f, indent=2)

        return spec

    def delete_custom_agent(self, agent_id: str) -> bool:
        if agent_id in self._agents and self._agents[agent_id].is_custom:
            del self._agents[agent_id]
            fpath = os.path.join(self._custom_agents_dir, f"{agent_id}.json")
            if os.path.exists(fpath):
                os.remove(fpath)
            return True
        return False

agent_forge = CustomAgentForge()
