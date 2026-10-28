import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

from server.config.env import settings
from server.core.core_platform.errors import CortexFailure
from server.core.core_platform.native_bridge import call_native
from server.core.core_platform.result import Ok, Result
from server.core.core_platform.zero_trust_crypto import ZeroTrustVault
from server.features.embodied_cortex.repository import EncryptedCortexRepository
from server.features.embodied_cortex.schemas import (
    ActiveInferenceStepRequest,
    ConsolidateShortcutRequest,
    QuadraticSolveRequest,
)

CORTICAL_FILE = Path("cortex") / "cortical_columns.sealed"
EMBODIED_FILE = Path("cortex") / "embodied_humanoid.sealed"
CORTICAL_PURPOSE = "cortical-columns"
EMBODIED_PURPOSE = "embodied-humanoid"
SHORTCUT_SIGN_PURPOSE = "cortical-shortcut-signature"
CORTICAL_AAD = b"nuxiva.cortex.cortical-columns.v1"
EMBODIED_AAD = b"nuxiva.cortex.embodied-humanoid.v1"
MILLISECONDS = 1000.0


class EmbodiedCortexService:
    def __init__(
        self,
        cortical_repo: EncryptedCortexRepository,
        embodied_repo: EncryptedCortexRepository,
        vault: ZeroTrustVault,
    ) -> None:
        self._cortical_repo = cortical_repo
        self._embodied_repo = embodied_repo
        self._vault = vault
        self._cortical: Any = None
        self._embodied: Any = None
        self._lock = threading.RLock()

    def _ensure_cortical(self) -> Result[Any, CortexFailure]:
        if self._cortical is not None:
            return Ok(self._cortical)
        loaded = self._cortical_repo.load()
        if loaded.is_ok and loaded.value is not None:
            restored = call_native(
                lambda native: native.RustCorticalCortex.from_snapshot_json(loaded.value)
            )
            if restored.is_ok:
                self._cortical = restored.value
                return restored
        fresh = call_native(lambda native: native.RustCorticalCortex())
        if fresh.is_ok:
            self._cortical = fresh.value
        return fresh

    def _ensure_embodied(self) -> Result[Any, CortexFailure]:
        if self._embodied is not None:
            return Ok(self._embodied)
        loaded = self._embodied_repo.load()
        if loaded.is_ok and loaded.value is not None:
            restored = call_native(
                lambda native: native.RustEmbodiedCortex.from_snapshot_json(loaded.value)
            )
            if restored.is_ok:
                self._embodied = restored.value
                return restored
        fresh = call_native(lambda native: native.RustEmbodiedCortex())
        if fresh.is_ok:
            self._embodied = fresh.value
        return fresh

    def _persist_cortical(self) -> Result[None, CortexFailure]:
        if self._cortical is None:
            return Ok(None)
        snap = call_native(lambda native: self._cortical.snapshot_json())
        if not snap.is_ok:
            return snap
        return self._cortical_repo.save(snap.value)

    def _persist_embodied(self) -> Result[None, CortexFailure]:
        if self._embodied is None:
            return Ok(None)
        snap = call_native(lambda native: self._embodied.snapshot_json())
        if not snap.is_ok:
            return snap
        return self._embodied_repo.save(snap.value)

    def overview(self) -> Result[Dict[str, Any], CortexFailure]:
        with self._lock:
            cortical_res = self._ensure_cortical()
            if not cortical_res.is_ok:
                return cortical_res
            embodied_res = self._ensure_embodied()
            if not embodied_res.is_ok:
                return embodied_res
            c_snap = call_native(lambda native: cortical_res.value.snapshot_json())
            if not c_snap.is_ok:
                return c_snap
            e_snap = call_native(lambda native: embodied_res.value.snapshot_json())
            if not e_snap.is_ok:
                return e_snap
            cortical_data = json.loads(c_snap.value)
            embodied_data = json.loads(e_snap.value)
            columns = cortical_data.get("columns", [])
            avg_maturity = (
                sum(float(c.get("maturity_score", 0.0)) for c in columns) / max(len(columns), 1)
            )
            joints = embodied_data.get("joints", [])
            avg_error = (
                sum(float(j.get("prediction_error_ema", 0.0)) for j in joints) / max(len(joints), 1)
            )
            embodied_alignment = max(0.0, min(1.0, 1.0 - avg_error * 4.0))
            human_parity_pct = round((avg_maturity * 48.0) + (embodied_alignment * 28.0), 1)
            return Ok(
                {
                    "cortical": cortical_data,
                    "embodied": embodied_data,
                    "metrics": {
                        "cortical_maturity_pct": round(avg_maturity * 100.0, 1),
                        "embodied_grounding_pct": round(embodied_alignment * 100.0, 1),
                        "estimated_human_logic_pct": human_parity_pct,
                        "rust_engine_version": "5.3.0",
                    },
                }
            )

    def solve_quadratic(self, req: QuadraticSolveRequest) -> Result[Dict[str, Any], CortexFailure]:
        started = time.perf_counter()
        with self._lock:
            cortical_res = self._ensure_cortical()
            if not cortical_res.is_ok:
                return cortical_res
            solved = call_native(
                lambda native: cortical_res.value.solve_quadratic_json(
                    req.column_id,
                    req.a,
                    req.b,
                    req.c,
                    req.tier,
                )
            )
            if not solved.is_ok:
                return solved
            persisted = self._persist_cortical()
            if not persisted.is_ok:
                return persisted
            payload = json.loads(solved.value)
            payload["latency_ms"] = round((time.perf_counter() - started) * MILLISECONDS, 3)
            return Ok(payload)

    def consolidate_shortcut(
        self, req: ConsolidateShortcutRequest
    ) -> Result[Dict[str, Any], CortexFailure]:
        with self._lock:
            cortical_res = self._ensure_cortical()
            if not cortical_res.is_ok:
                return cortical_res
            consolidated = call_native(
                lambda native: cortical_res.value.consolidate_shortcut_json(
                    req.pattern_signature,
                    req.a,
                    req.b,
                    req.c,
                )
            )
            if not consolidated.is_ok:
                return consolidated
            persisted = self._persist_cortical()
            if not persisted.is_ok:
                return persisted
            shortcut_data = json.loads(consolidated.value)
            signed = self._vault.sign(
                SHORTCUT_SIGN_PURPOSE,
                consolidated.value.encode("utf-8"),
            )
            if signed.is_ok:
                shortcut_data["ed25519_signature_hex"] = signed.value.signature.hex()[:32]
            return Ok(shortcut_data)

    def step_active_inference(
        self, req: ActiveInferenceStepRequest
    ) -> Result[Dict[str, Any], CortexFailure]:
        started = time.perf_counter()
        with self._lock:
            embodied_res = self._ensure_embodied()
            if not embodied_res.is_ok:
                return embodied_res
            cmd_json = json.dumps(
                {
                    "joint_id": req.joint_id,
                    "target_angle_rad": req.target_angle_rad,
                    "feedforward_torque_nm": req.feedforward_torque_nm,
                    "dt_sec": req.dt_sec,
                    "measured_load_kg": req.measured_load_kg,
                }
            )
            stepped = call_native(
                lambda native: embodied_res.value.step_active_inference_json(
                    cmd_json,
                    req.measured_angle_override,
                )
            )
            if not stepped.is_ok:
                return stepped
            persisted = self._persist_embodied()
            if not persisted.is_ok:
                return persisted
            payload = json.loads(stepped.value)
            payload["latency_ms"] = round((time.perf_counter() - started) * MILLISECONDS, 3)
            return Ok(payload)


_service: Optional[EmbodiedCortexService] = None
_service_lock = threading.Lock()


def build_embodied_cortex_service(data_dir: Optional[Path] = None) -> EmbodiedCortexService:
    base_dir = data_dir if data_dir is not None else Path(settings.DATA_DIR)
    vault = ZeroTrustVault(lambda: settings.NUXIVA_SECRET_KEY)
    cortical_repo = EncryptedCortexRepository(
        base_dir / CORTICAL_FILE,
        vault,
        CORTICAL_PURPOSE,
        CORTICAL_AAD,
    )
    embodied_repo = EncryptedCortexRepository(
        base_dir / EMBODIED_FILE,
        vault,
        EMBODIED_PURPOSE,
        EMBODIED_AAD,
    )
    return EmbodiedCortexService(cortical_repo, embodied_repo, vault)


def embodied_cortex_service() -> EmbodiedCortexService:
    global _service
    with _service_lock:
        if _service is None:
            _service = build_embodied_cortex_service()
        return _service
