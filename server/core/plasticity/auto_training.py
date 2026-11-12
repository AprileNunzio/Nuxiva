import asyncio
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Optional

from server.core.core_platform.errors import CortexFailure
from server.core.core_platform.result import Ok, Result
from server.core.plasticity import distillation
from server.core.plasticity.ledger import PlasticityLedger

logger = logging.getLogger("nuxiva.plasticity.training")

CONSENT_KEY = "NUXIVA_CORTEX_TRAINING"
MODEL_KEY = "NUXIVA_CORTEX_TRAIN_MODEL"
DEFAULT_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
CONSENT_VALUES = frozenset({"1", "on", "yes", "true", "auto"})
PACKAGES = ("torch", "transformers", "peft", "bitsandbytes", "datasets", "trl", "accelerate")
RETRAIN_DAYS = 7.0
INSTALL_RETRY_DAYS = 7.0
INSTALL_TIMEOUT_SECONDS = 3_600
META_TRAINED = "last_training"
META_INSTALL = "last_dependency_attempt"
DATASET = Path("cortex") / "distillation.jsonl"
ADAPTER = Path("cortex") / "adapter"


def gpu_detected() -> bool:
    if shutil.which("nvidia-smi") or Path("/dev/nvidia0").exists():
        return True
    return distillation.gpu_available()


def consent_given(environment: Optional[dict[str, str]] = None) -> bool:
    source = os.environ if environment is None else environment
    return source.get(CONSENT_KEY, "").strip().lower() in CONSENT_VALUES


def install_dependencies(missing: list[str]) -> bool:
    allowed = [name for name in missing if name in PACKAGES]
    if not allowed:
        return True
    command = [sys.executable, "-m", "pip", "install", "--no-input", "--disable-pip-version-check", *allowed]
    try:
        done = subprocess.run(command, capture_output=True, timeout=INSTALL_TIMEOUT_SECONDS, check=False)
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.error("Training dependencies not installed (%s)", type(exc).__name__)
        return False
    if done.returncode != 0:
        logger.error("Training dependencies not installed (pip exit %s)", done.returncode)
    return done.returncode == 0


class AutoTrainer:
    def __init__(self, ledger: PlasticityLedger, data_dir: Path, installer: Callable[[list[str]], bool] = install_dependencies,
                 detector: Callable[[], bool] = gpu_detected, trainer: Callable[..., Result] = distillation.train,
                 environment: Optional[dict[str, str]] = None) -> None:
        self._ledger = ledger
        self._data = data_dir
        self._install = installer
        self._detect = detector
        self._train = trainer
        self._environment = environment

    def status(self) -> Result[dict[str, Any], CortexFailure]:
        totals = self._ledger.totals()
        trained = self._ledger.meta(META_TRAINED)
        for part in (totals, trained):
            if not part.is_ok:
                return part
        gpu = self._detect()
        consent = consent_given(self._environment)
        ready = totals.value["examples"] >= distillation.MIN_EXAMPLES
        state = "no_gpu" if not gpu else "waiting_for_data" if not ready else "ready" if consent else "consent_required"
        return Ok({"gpu_detected": gpu, "consent": consent, "examples": totals.value["examples"],
                   "needed": distillation.MIN_EXAMPLES, "last_trained": trained.value, "state": state,
                   "missing": distillation.missing_dependencies()})

    async def cycle(self, now: Optional[float] = None) -> Result[dict[str, Any], CortexFailure]:
        moment = time.time() if now is None else now
        current = await asyncio.to_thread(self.status)
        if not current.is_ok or current.value["state"] != "ready":
            return current
        last = current.value["last_trained"]
        if last is not None and (moment - last) < RETRAIN_DAYS * 86_400.0:
            return Ok({**current.value, "state": "recent"})
        missing = current.value["missing"]
        if missing and not await self._ensure(missing, moment):
            return Ok({**current.value, "state": "dependencies_unavailable"})
        return await asyncio.to_thread(self._run, moment)

    async def _ensure(self, missing: list[str], moment: float) -> bool:
        attempted = await asyncio.to_thread(self._ledger.meta, META_INSTALL)
        if attempted.is_ok and attempted.value is not None and (moment - attempted.value) < INSTALL_RETRY_DAYS * 86_400.0:
            return False
        await asyncio.to_thread(self._ledger.set_meta, META_INSTALL, moment)
        installed = await asyncio.to_thread(self._install, missing)
        return installed and not distillation.missing_dependencies()

    def _run(self, moment: float) -> Result[dict[str, Any], CortexFailure]:
        built = distillation.build_dataset(self._ledger, self._data / DATASET)
        if not built.is_ok:
            return built
        base = (self._environment if self._environment is not None else os.environ).get(MODEL_KEY, "").strip() or DEFAULT_MODEL
        trained = self._train(self._data / DATASET, base, self._data / ADAPTER)
        if not trained.is_ok:
            logger.error("Automatic training failed (%s)", trained.error.code)
            return trained
        self._ledger.set_meta(META_TRAINED, moment)
        logger.info("Adapter trained on %d examples", built.value)
        return Ok({"state": "trained", "examples": built.value, **trained.value})
