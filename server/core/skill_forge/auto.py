import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from server.core.core_platform.errors import CortexFailure
from server.core.core_platform.result import Ok, Result
from server.core.hippocampus_router.hippocampus_service import HippocampusService
from server.core.skill_forge import author, mining
from server.core.skill_forge.forge import SkillForge
from server.core.skill_forge.misses import MissLedger

logger = logging.getLogger("nuxiva.skill_forge.auto")

Completion = Callable[[str, str], Awaitable[str]]


@dataclass(frozen=True, slots=True)
class AutoLimits:
    per_cycle: int = 3
    retry_days: float = 7.0
    max_total: int = 200


class AutoForge:
    def __init__(self, forge: SkillForge, hippocampus: HippocampusService, ledger: MissLedger, complete: Completion,
                 limits: AutoLimits = AutoLimits()) -> None:
        self._forge = forge
        self._hippocampus = hippocampus
        self._ledger = ledger
        self._complete = complete
        self._limits = limits

    def note(self, utterance: str) -> None:
        stored = self._ledger.note(utterance)
        if not stored.is_ok:
            logger.error("Slow-path request not recorded (%s)", stored.error.code)

    def status(self) -> Result[dict[str, Any], CortexFailure]:
        pending, attempts = self._ledger.count(), self._ledger.attempts()
        for part in (pending, attempts):
            if not part.is_ok:
                return part
        return Ok({"pending_requests": pending.value, "recent_attempts": attempts.value,
                   "minimum_cluster": mining.MIN_CLUSTER, "per_cycle": self._limits.per_cycle})

    def _candidates(self) -> Result[list[list[str]], CortexFailure]:
        texts = self._ledger.recent()
        if not texts.is_ok:
            return texts
        if len(texts.value) < mining.MIN_CLUSTER:
            return Ok([])
        vectors = self._hippocampus.embed_many(texts.value)
        if not vectors.is_ok:
            return vectors
        return Ok(mining.cluster(texts.value, vectors.value))

    def _owned(self) -> Result[set[str], CortexFailure]:
        listing = self._forge.listing()
        return listing if not listing.is_ok else Ok({item["neuron_id"] for item in listing.value})

    async def cycle(self) -> Result[dict[str, Any], CortexFailure]:
        found = await asyncio.to_thread(self._candidates)
        if not found.is_ok:
            return found
        report: dict[str, Any] = {"clusters": len(found.value), "forged": [], "rejected": 0, "skipped": 0}
        owned = await asyncio.to_thread(self._owned)
        if not owned.is_ok:
            return owned
        if len(owned.value) >= self._limits.max_total:
            report["skipped"] = len(found.value)
            return Ok(report)
        spent = 0
        for group in found.value:
            if spent >= self._limits.per_cycle:
                report["skipped"] += 1
                continue
            attempted, neuron_id = await self._attempt(group, owned.value)
            if not attempted:
                report["skipped"] += 1
                continue
            spent += 1
            if neuron_id:
                report["forged"].append(neuron_id)
                owned.value.add(neuron_id)
            else:
                report["rejected"] += 1
        return Ok(report)

    async def _attempt(self, group: list[str], owned: set[str]) -> tuple[bool, str]:
        key = mining.key(group)
        recent = await asyncio.to_thread(self._ledger.tried_recently, key, self._limits.retry_days)
        if not recent.is_ok or recent.value:
            return False, ""
        outcome, neuron_id = await self._author_and_forge(group, owned)
        await asyncio.to_thread(self._ledger.record_attempt, key, outcome)
        if neuron_id:
            await asyncio.to_thread(self._ledger.settled, group)
            logger.info("Skill %s forged from %d recurring requests", neuron_id, len(group))
        return True, neuron_id

    async def _author_and_forge(self, group: list[str], owned: set[str]) -> tuple[str, str]:
        try:
            raw = await self._complete(author.SYSTEM, author.prompt(mining.examples(group)))
        except Exception as exc:
            logger.warning("Skill authoring unavailable (%s)", type(exc).__name__)
            return "model_unavailable", ""
        authored = author.parse(raw)
        if not authored.is_ok:
            return authored.error.code, ""
        if authored.value is None:
            return "not_forgeable", ""
        if authored.value.manifest["neuron_id"] in owned:
            return "id_taken", ""
        forged = await asyncio.to_thread(self._forge.forge, authored.value.manifest, authored.value.source, "forge")
        if not forged.is_ok:
            logger.info("Authored skill rejected (%s)", forged.error.code)
            return forged.error.code, ""
        return "forged", forged.value["neuron_id"]

