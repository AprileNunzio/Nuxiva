from pathlib import Path

import packages
from config import STATE_DIR, VERSION, read_env
from feature_registry import registry
from state import store
from steps import STEPS

from agenti.autonomy import approvals
from agenti.nexus.application.awakening_service import AwakeningService
from agenti.nexus.application.freshness_service import FreshnessService
from agenti.nexus.application.preferences_service import PreferencesService
from agenti.nexus.application.summary_service import SummaryService
from agenti.nexus.application.tool_service import ToolService
from agenti.nexus.infrastructure.fingerprint import FolderFingerprint
from agenti.nexus.infrastructure.json_preferences import JsonPreferencesRepository
from agenti.nexus.infrastructure.json_store import JsonDocument


def _catalog() -> dict:
    registry.scan()
    return registry.listing()


def feature_folders() -> dict[str, Path]:
    return {fid: Path(m["dir"]) for fid, m in list(registry.features.items()) if m.get("dir")}


awakening = AwakeningService(JsonDocument(STATE_DIR / "nexus" / "awakening.json"), env=read_env, catalog=_catalog,
                             brain_mode=packages.brain_mode)
freshness = FreshnessService(FolderFingerprint(ignore=(VERSION,)), JsonDocument(STATE_DIR / "nexus" / "freshness.json"),
                             revision="2")
preferences = PreferencesService(JsonPreferencesRepository(STATE_DIR / "nexus" / "preferences.json"))
summary = SummaryService(state=lambda: store.snapshot(admin=True, log_lines=0), catalog=_catalog,
                         step_titles=lambda: {s.id: s.title for s in STEPS}, approvals=lambda: len(approvals.pending()),
                         badges=freshness.badges, awakening=awakening.progress)
tools = ToolService(catalog=_catalog, badges=freshness.badges)
