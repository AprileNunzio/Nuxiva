import logging
from typing import Any, Mapping, Optional

from server.core.core_platform.errors import CortexFailure, fail
from server.core.core_platform.result import Err, Ok, Result
from server.core.hippocampus_router.hippocampus_service import HippocampusService
from server.core.skill_forge.ast_scanner import scan_source
from server.core.skill_forge.contracts import SkillManifest
from server.core.skill_forge.sandbox import run_isolated
from server.core.skill_forge.store import SkillStore
from server.core.skill_forge.synthetic import expand

logger = logging.getLogger("nuxiva.skill_forge")

ORIGINS = frozenset({"manual", "forge"})


class SkillForge:
    def __init__(self, hippocampus: HippocampusService, store: SkillStore) -> None:
        self._hippocampus = hippocampus
        self._store = store

    def forge(self, manifest_data: Any, source: str, origin: str = "manual") -> Result[dict[str, Any], CortexFailure]:
        manifest = SkillManifest.parse(manifest_data)
        if not manifest.is_ok:
            return manifest
        if origin not in ORIGINS:
            return fail("cortex.forge.manifest_invalid")
        scanned = scan_source(source)
        if not scanned.is_ok:
            return scanned
        proven = self._prove(manifest.value, source)
        if not proven.is_ok:
            return proven
        utterances, synthetic = expand(manifest.value.utterances, manifest.value.slot_schema)
        payload = {"neuron_id": manifest.value.neuron_id, "source": source,
                   "slot_schema": [dict(item) for item in manifest.value.slot_schema]}
        stored = self._store.put(manifest.value.neuron_id, manifest.value.title, payload, origin, synthetic)
        if not stored.is_ok:
            return stored
        learned = self._hippocampus.learn(manifest.value.neuron_id, utterances)
        if not learned.is_ok:
            self._rollback(manifest.value.neuron_id)
            return learned
        return Ok({"neuron_id": manifest.value.neuron_id, "utterances": learned.value, "synthetic": synthetic,
                   "cases_passed": len(manifest.value.cases)})

    def _prove(self, manifest: SkillManifest, source: str) -> Result[None, CortexFailure]:
        for case in manifest.cases:
            outcome = run_isolated(source, case.slots)
            if not outcome.is_ok:
                return outcome
            if outcome.value["speech"] != case.expect_speech:
                return fail("cortex.forge.output_invalid", expected=case.expect_speech)
        return Ok(None)

    def _rollback(self, neuron_id: str) -> None:
        removed = self._store.remove(neuron_id)
        if not removed.is_ok:
            logger.error("Skill %s could not be rolled back (%s)", neuron_id, removed.error.code)

    def retire(self, neuron_id: str) -> Result[bool, CortexFailure]:
        removed = self._store.remove(neuron_id)
        if not removed.is_ok:
            return removed
        if removed.value:
            self._hippocampus.forget(neuron_id)
        return removed

    def listing(self) -> Result[list[dict[str, Any]], CortexFailure]:
        return self._store.listing()


class SkillRuntime:
    def __init__(self, store: SkillStore) -> None:
        self._store = store

    def slot_schema(self, neuron_id: str) -> Optional[list[Mapping[str, Any]]]:
        trusted = self._store.trusted_payload(neuron_id)
        return trusted.value.get("slot_schema") if trusted.is_ok else None

    def execute(self, neuron_id: str, slots: Mapping[str, Any]) -> Result[dict[str, Any], CortexFailure]:
        trusted = self._store.trusted_payload(neuron_id)
        if not trusted.is_ok:
            return trusted
        source = trusted.value.get("source")
        if not isinstance(source, str):
            return Err(CortexFailure("cortex.forge.untrusted"))
        rescanned = scan_source(source)
        if not rescanned.is_ok:
            return rescanned
        return run_isolated(source, slots)
