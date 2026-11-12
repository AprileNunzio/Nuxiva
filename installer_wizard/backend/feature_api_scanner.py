import importlib
import logging
from pathlib import Path

logger = logging.getLogger("nuxiva.feature_api_scanner")


def _system_agents(root_dir: Path | None):
    from agenti._registry import AgentRegistry, SYSTEM_DIR, root
    legacy = root_dir or Path(__file__).resolve().parents[1] / "features"
    roots = [root(legacy, "legacy", "flat")] if root_dir else [root(SYSTEM_DIR, "system", "categorized"), root(legacy, "legacy", "flat")]
    return AgentRegistry(lambda: roots).agents()


def _raw(agent) -> dict:
    import json
    return json.loads(agent.manifest_path.read_text(encoding="utf-8"))


def discover_feature_apis(root: Path | None = None):
    modules = []
    for agent in _system_agents(root):
        try:
            if _raw(agent).get("api") != "api.py" or not agent.module:
                continue
            modules.append(importlib.import_module(f"{agent.module}.api"))
        except (OSError, ValueError, ImportError) as exc:
            logger.warning("Feature API unavailable: %s (%s)", agent.id, type(exc).__name__)
    return modules


def discover_feature_connectors(root: Path | None = None):
    from features.authz.risk import CONNECTORS, Risk, parse
    connectors = {}
    for agent in _system_agents(root):
        try:
            data = _raw(agent)
        except (OSError, ValueError):
            continue
        if data.get("connector") == "commands.py" and agent.module:
            risk = parse(data.get("connector_risk"))
            CONNECTORS[agent.id] = risk if risk is not None else Risk.CRITICAL
            connectors[agent.id] = f"{agent.module}.commands"
    return connectors
