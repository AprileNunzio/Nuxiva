import logging
import time
from typing import Any, Optional

from server.core.core_platform.errors import CortexFailure, fail
from server.core.core_platform.result import Ok, Result
from server.core.hippocampus_router.hippocampus_service import HippocampusService
from server.core.plasticity import rules
from server.core.plasticity.ledger import PlasticityLedger

logger = logging.getLogger("nuxiva.plasticity")

OUTCOMES = frozenset({"success", "failure", "corrected"})
MAX_UTTERANCE_CHARS = 500


class PlasticityService:
    def __init__(self, hippocampus: HippocampusService, ledger: PlasticityLedger, protected: Any = None, retire: Any = None) -> None:
        self._hippocampus = hippocampus
        self._ledger = ledger
        self._protected = protected or (lambda neuron_id: False)
        self._retire = retire or (lambda neuron_id: Ok(False))

    def feedback(self, neuron_id: str, utterance: str, outcome: str, corrected_to: Optional[str] = None,
                 now: Optional[float] = None) -> Result[dict[str, Any], CortexFailure]:
        if outcome not in OUTCOMES or not isinstance(utterance, str) or not 0 < len(utterance.strip()) <= MAX_UTTERANCE_CHARS:
            return fail("cortex.plasticity.invalid")
        if outcome == "corrected" and not corrected_to:
            return fail("cortex.plasticity.invalid")
        weights = self._hippocampus.weights()
        if not weights.is_ok:
            return weights
        if neuron_id not in weights.value or (corrected_to and corrected_to not in weights.value):
            return fail("cortex.neuron.unknown")
        if outcome == "success":
            return self._succeed(neuron_id, utterance, weights.value[neuron_id], now)
        return self._punish(neuron_id, utterance, weights.value[neuron_id], corrected_to, weights.value, now)

    def _succeed(self, neuron_id: str, utterance: str, weight: float, now: Optional[float]) -> Result[dict[str, Any], CortexFailure]:
        grown = self._hippocampus.reinforce_with(neuron_id, utterance)
        if not grown.is_ok:
            return grown
        raised = self._hippocampus.set_weight(neuron_id, rules.potentiate(weight))
        if not raised.is_ok:
            return raised
        self._record(neuron_id, True, utterance, now)
        return Ok({"neuron_id": neuron_id, "weight": round(raised.value, 4), "change": "potentiated"})

    def _punish(self, neuron_id: str, utterance: str, weight: float, corrected_to: Optional[str],
                weights: dict[str, float], now: Optional[float]) -> Result[dict[str, Any], CortexFailure]:
        inhibited = self._hippocampus.reinforce_with(neuron_id, utterance, inhibit=True)
        if not inhibited.is_ok:
            return inhibited
        lowered = self._hippocampus.set_weight(neuron_id, rules.depress(weight))
        if not lowered.is_ok:
            return lowered
        self._record(neuron_id, False, utterance, now)
        report: dict[str, Any] = {"neuron_id": neuron_id, "weight": round(lowered.value, 4), "change": "depressed"}
        if corrected_to:
            target = self._succeed(corrected_to, utterance, weights[corrected_to], now)
            if not target.is_ok:
                return target
            report["corrected_to"] = target.value
        return Ok(report)

    def _record(self, neuron_id: str, success: bool, utterance: str, now: Optional[float]) -> None:
        touched = self._ledger.touch(neuron_id, success, now)
        if not touched.is_ok:
            logger.error("Plasticity usage not recorded for %s (%s)", neuron_id, touched.error.code)
        if success:
            added = self._ledger.add_example(neuron_id, utterance.strip(), now)
            if not added.is_ok:
                logger.error("Plasticity example not stored for %s (%s)", neuron_id, added.error.code)

    def consolidate(self, now: Optional[float] = None) -> Result[dict[str, Any], CortexFailure]:
        moment = time.time() if now is None else now
        weights = self._hippocampus.weights()
        if not weights.is_ok:
            return weights
        previous = self._ledger.last_run()
        if not previous.is_ok:
            return previous
        elapsed = 1.0 if previous.value is None else min(rules.MAX_ELAPSED_DAYS, max(0.0, (moment - previous.value) / 86_400.0))
        decayed, pruned, kept = [], [], 0
        for neuron_id, weight in sorted(weights.value.items()):
            idle = self._ledger.idle_days(neuron_id, moment)
            if not idle.is_ok:
                return idle
            if rules.should_prune(weight, idle.value, bool(self._protected(neuron_id))):
                self._prune(neuron_id, pruned)
                continue
            lowered = rules.decay(weight, elapsed) if idle.value > rules.GRACE_DAYS else weight
            if abs(lowered - weight) > 1e-4 and not self._protected(neuron_id):
                changed = self._hippocampus.set_weight(neuron_id, lowered)
                if not changed.is_ok:
                    return changed
                decayed.append(neuron_id)
            kept += 1
        marked = self._ledger.mark_run(moment)
        if not marked.is_ok:
            return marked
        return Ok({"decayed": decayed, "pruned": pruned, "kept": kept, "at": moment})

    def _prune(self, neuron_id: str, pruned: list[str]) -> None:
        removed = self._hippocampus.forget(neuron_id)
        if not removed.is_ok:
            logger.error("Neuron %s could not be pruned (%s)", neuron_id, removed.error.code)
            return
        self._ledger.forget(neuron_id)
        retired = self._retire(neuron_id)
        if not retired.is_ok:
            logger.error("Skill %s could not be retired after pruning (%s)", neuron_id, retired.error.code)
        pruned.append(neuron_id)

    def last_run(self) -> Result[Any, CortexFailure]:
        return self._ledger.last_run()

    def status(self) -> Result[Any, CortexFailure]:
        return self._ledger.totals()
