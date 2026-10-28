use std::sync::RwLock;

use nuxiva_cortex_core::{
    AbstractionTier, CanOpenPdoFrame, Cia402State, CortexError as CoreError, CorticalCortex,
    EmbodiedCortex, EpistemicDoubtEngine, EpistemicHypothesis, EtherCatLrwFrame,
    FieldbusController, FormalismParadigm, HumanoidKinematics34, MotorCommand,
    OntologicalCreativeEngine,
};
use pyo3::prelude::*;

use crate::cortex::CortexError;
use crate::errors::poisoned;

fn failure(error: CoreError) -> PyErr {
    CortexError::new_err(error.code())
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug, Default)]
pub struct RustCorticalCortex {
    inner: RwLock<CorticalCortex>,
}

impl RustCorticalCortex {
    fn read<T>(&self, action: impl FnOnce(&CorticalCortex) -> T) -> PyResult<T> {
        self.inner
            .read()
            .map(|guard| action(&guard))
            .map_err(|_| poisoned())
    }

    fn write<T>(&self, action: impl FnOnce(&mut CorticalCortex) -> T) -> PyResult<T> {
        self.inner
            .write()
            .map(|mut guard| action(&mut guard))
            .map_err(|_| poisoned())
    }
}

#[pymethods]
impl RustCorticalCortex {
    #[new]
    fn new() -> Self {
        Self {
            inner: RwLock::new(CorticalCortex::new()),
        }
    }

    #[staticmethod]
    fn from_snapshot_json(snapshot: &str) -> PyResult<Self> {
        Ok(Self {
            inner: RwLock::new(CorticalCortex::from_snapshot_json(snapshot).map_err(failure)?),
        })
    }

    fn snapshot_json(&self) -> PyResult<String> {
        self.read(CorticalCortex::snapshot_json)?.map_err(failure)
    }

    #[pyo3(signature = (column_id, a, b, c, tier = None))]
    fn solve_quadratic_json(
        &self,
        py: Python<'_>,
        column_id: &str,
        a: f64,
        b: f64,
        c: f64,
        tier: Option<&str>,
    ) -> PyResult<String> {
        let parsed_tier = match tier {
            Some(name) => Some(
                AbstractionTier::from_name(name)
                    .ok_or_else(|| failure(CoreError::InvalidExpression))?,
            ),
            None => None,
        };
        let resolution = py
            .detach(|| {
                self.write(|cortex| cortex.solve_quadratic(column_id, a, b, c, parsed_tier))
            })?
            .map_err(failure)?;
        serde_json::to_string(&resolution).map_err(|_| failure(CoreError::SnapshotInvalid))
    }

    fn consolidate_shortcut_json(
        &self,
        pattern_signature: &str,
        a: f64,
        b: f64,
        c: f64,
    ) -> PyResult<String> {
        let shortcut = self
            .write(|cortex| cortex.consolidate_shortcut(pattern_signature, a, b, c))?
            .map_err(failure)?;
        serde_json::to_string(&shortcut).map_err(|_| failure(CoreError::SnapshotInvalid))
    }
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug, Default)]
pub struct RustEmbodiedCortex {
    inner: RwLock<EmbodiedCortex>,
}

impl RustEmbodiedCortex {
    fn read<T>(&self, action: impl FnOnce(&EmbodiedCortex) -> T) -> PyResult<T> {
        self.inner
            .read()
            .map(|guard| action(&guard))
            .map_err(|_| poisoned())
    }

    fn write<T>(&self, action: impl FnOnce(&mut EmbodiedCortex) -> T) -> PyResult<T> {
        self.inner
            .write()
            .map(|mut guard| action(&mut guard))
            .map_err(|_| poisoned())
    }
}

#[pymethods]
impl RustEmbodiedCortex {
    #[new]
    fn new() -> Self {
        Self {
            inner: RwLock::new(EmbodiedCortex::new()),
        }
    }

    #[staticmethod]
    fn from_snapshot_json(snapshot: &str) -> PyResult<Self> {
        Ok(Self {
            inner: RwLock::new(EmbodiedCortex::from_snapshot_json(snapshot).map_err(failure)?),
        })
    }

    fn snapshot_json(&self) -> PyResult<String> {
        self.read(EmbodiedCortex::snapshot_json)?.map_err(failure)
    }

    #[pyo3(signature = (command_json, measured_angle_override = None))]
    fn step_active_inference_json(
        &self,
        py: Python<'_>,
        command_json: &str,
        measured_angle_override: Option<f64>,
    ) -> PyResult<String> {
        let cmd: MotorCommand = serde_json::from_str(command_json)
            .map_err(|_| failure(CoreError::InvalidExpression))?;
        let step = py
            .detach(|| {
                self.write(|embodied| embodied.step_active_inference(&cmd, measured_angle_override))
            })?
            .map_err(failure)?;
        serde_json::to_string(&step).map_err(|_| failure(CoreError::SnapshotInvalid))
    }
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug, Default)]
pub struct RustEpistemicDoubtEngine {
    inner: RwLock<EpistemicDoubtEngine>,
}

#[pymethods]
impl RustEpistemicDoubtEngine {
    #[new]
    fn new() -> Self {
        Self {
            inner: RwLock::new(EpistemicDoubtEngine::default()),
        }
    }

    fn should_confront_json(&self, hypotheses_json: &str) -> PyResult<bool> {
        let hypotheses: Vec<EpistemicHypothesis> = serde_json::from_str(hypotheses_json)
            .map_err(|_| failure(CoreError::InvalidExpression))?;
        let guard = self.inner.read().map_err(|_| poisoned())?;
        Ok(guard.should_confront(&hypotheses))
    }

    fn initiate_confrontation_json(
        &self,
        id: &str,
        context_key: &str,
        hypotheses_json: &str,
        epoch_ms: u64,
    ) -> PyResult<String> {
        let hypotheses: Vec<EpistemicHypothesis> = serde_json::from_str(hypotheses_json)
            .map_err(|_| failure(CoreError::InvalidExpression))?;
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        let record = guard
            .initiate_confrontation(
                id.to_string(),
                context_key.to_string(),
                hypotheses,
                epoch_ms,
            )
            .map_err(failure)?;
        serde_json::to_string(&record).map_err(|_| failure(CoreError::SnapshotInvalid))
    }

    fn resolve_confrontation_json(
        &self,
        id: &str,
        choice_id: &str,
        justification: &str,
        resolved_epoch_ms: u64,
    ) -> PyResult<String> {
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        let record = guard
            .resolve_confrontation(id, choice_id, justification, resolved_epoch_ms)
            .map_err(failure)?;
        serde_json::to_string(&record).map_err(|_| failure(CoreError::SnapshotInvalid))
    }

    fn lookup_prior_json(&self, context_key: &str) -> PyResult<Option<String>> {
        let guard = self.inner.read().map_err(|_| poisoned())?;
        match guard.lookup_prior(context_key) {
            Some(rec) => {
                let json =
                    serde_json::to_string(rec).map_err(|_| failure(CoreError::SnapshotInvalid))?;
                Ok(Some(json))
            }
            None => Ok(None),
        }
    }

    fn list_pending_json(&self) -> PyResult<String> {
        let guard = self.inner.read().map_err(|_| poisoned())?;
        serde_json::to_string(&guard.list_pending())
            .map_err(|_| failure(CoreError::SnapshotInvalid))
    }

    fn list_resolved_json(&self) -> PyResult<String> {
        let guard = self.inner.read().map_err(|_| poisoned())?;
        serde_json::to_string(&guard.list_resolved())
            .map_err(|_| failure(CoreError::SnapshotInvalid))
    }
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug, Default)]
pub struct RustOntologicalCreativeEngine {
    inner: RwLock<OntologicalCreativeEngine>,
}

#[pymethods]
impl RustOntologicalCreativeEngine {
    #[new]
    fn new() -> Self {
        Self {
            inner: RwLock::new(OntologicalCreativeEngine::new()),
        }
    }

    #[staticmethod]
    fn detect_anomaly(observations_json: &str, threshold: f64) -> PyResult<f64> {
        let obs: Vec<(f64, f64)> = serde_json::from_str(observations_json)
            .map_err(|_| failure(CoreError::InvalidExpression))?;
        OntologicalCreativeEngine::detect_anomaly(&obs, threshold).map_err(failure)
    }

    fn synthesize_formalism_json(
        &self,
        id: &str,
        paradigm_name: &str,
        observations_json: &str,
    ) -> PyResult<String> {
        let obs: Vec<(f64, f64)> = serde_json::from_str(observations_json)
            .map_err(|_| failure(CoreError::InvalidExpression))?;
        let paradigm = match paradigm_name {
            "calculus" => FormalismParadigm::Calculus,
            "riemann_metric" => FormalismParadigm::RiemannMetric,
            "lie_algebra" => FormalismParadigm::LieAlgebra,
            "symplectic_geometry" => FormalismParadigm::SymplecticGeometry,
            "discrete_topology" => FormalismParadigm::DiscreteTopology,
            _ => return Err(failure(CoreError::InvalidExpression)),
        };
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        let formalism = guard
            .synthesize_formalism(id.to_string(), paradigm, &obs)
            .map_err(failure)?;
        serde_json::to_string(&formalism).map_err(|_| failure(CoreError::SnapshotInvalid))
    }

    fn list_synthesized_json(&self) -> PyResult<String> {
        let guard = self.inner.read().map_err(|_| poisoned())?;
        serde_json::to_string(guard.list_synthesized())
            .map_err(|_| failure(CoreError::SnapshotInvalid))
    }
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug, Default)]
pub struct RustHumanoidKinematics34 {
    inner: RwLock<HumanoidKinematics34>,
}

#[pymethods]
impl RustHumanoidKinematics34 {
    #[new]
    fn new() -> Self {
        Self {
            inner: RwLock::new(HumanoidKinematics34::new()),
        }
    }

    fn joint_count(&self) -> PyResult<usize> {
        let guard = self.inner.read().map_err(|_| poisoned())?;
        Ok(guard.joint_count())
    }

    fn enforce_limits(&self, joint_id: &str, target_rad: f64) -> PyResult<f64> {
        let guard = self.inner.read().map_err(|_| poisoned())?;
        guard.enforce_limits(joint_id, target_rad).map_err(failure)
    }

    fn update_joint(
        &self,
        joint_id: &str,
        angle_rad: f64,
        velocity_rad_s: f64,
        torque_nm: f64,
        temperature_c: f64,
    ) -> PyResult<()> {
        let mut guard = self.inner.write().map_err(|_| poisoned())?;
        guard
            .update_joint(
                joint_id,
                angle_rad,
                velocity_rad_s,
                torque_nm,
                temperature_c,
            )
            .map_err(failure)
    }

    fn forward_kinematics_hand_json(&self, is_right: bool) -> PyResult<String> {
        let guard = self.inner.read().map_err(|_| poisoned())?;
        let pose = guard.forward_kinematics_hand(is_right);
        serde_json::to_string(&pose).map_err(|_| failure(CoreError::SnapshotInvalid))
    }

    fn list_joints_json(&self) -> PyResult<String> {
        let guard = self.inner.read().map_err(|_| poisoned())?;
        serde_json::to_string(&guard.list_all_joints())
            .map_err(|_| failure(CoreError::SnapshotInvalid))
    }
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct RustFieldbusController;

#[pymethods]
impl RustFieldbusController {
    #[staticmethod]
    #[allow(clippy::fn_params_excessive_bools)]
    fn encode_controlword(
        switch_on: bool,
        enable_voltage: bool,
        quick_stop: bool,
        enable_op: bool,
        fault_reset: bool,
    ) -> u16 {
        FieldbusController::encode_controlword(
            switch_on,
            enable_voltage,
            quick_stop,
            enable_op,
            fault_reset,
        )
    }

    #[staticmethod]
    fn parse_statusword(statusword: u16) -> String {
        FieldbusController::parse_statusword(statusword)
            .as_str()
            .to_string()
    }

    #[staticmethod]
    fn transition_cia402(current_state_str: &str, controlword: u16) -> PyResult<String> {
        let current = match current_state_str {
            "not_ready_to_switch_on" => Cia402State::NotReadyToSwitchOn,
            "switch_on_disabled" => Cia402State::SwitchOnDisabled,
            "ready_to_switch_on" => Cia402State::ReadyToSwitchOn,
            "switched_on" => Cia402State::SwitchedOn,
            "operation_enabled" => Cia402State::OperationEnabled,
            "quick_stop_active" => Cia402State::QuickStopActive,
            "fault_reaction_active" => Cia402State::FaultReactionActive,
            "fault" => Cia402State::Fault,
            _ => return Err(failure(CoreError::InvalidExpression)),
        };
        Ok(FieldbusController::transition_cia402(current, controlword)
            .as_str()
            .to_string())
    }

    #[staticmethod]
    fn build_rpdo1_position_json(
        node_id: u8,
        target_pulse: i32,
        controlword: u16,
    ) -> PyResult<String> {
        let frame = FieldbusController::build_rpdo1_position(node_id, target_pulse, controlword);
        serde_json::to_string(&frame).map_err(|_| failure(CoreError::SnapshotInvalid))
    }

    #[staticmethod]
    fn parse_tpdo1_position_json(frame_json: &str) -> PyResult<(u16, i32)> {
        let frame: CanOpenPdoFrame =
            serde_json::from_str(frame_json).map_err(|_| failure(CoreError::InvalidExpression))?;
        FieldbusController::parse_tpdo1_position(&frame).map_err(failure)
    }

    #[staticmethod]
    fn verify_ethercat_lrw(working_counter: u16, expected_wkc: u16) -> PyResult<bool> {
        let frame = EtherCatLrwFrame {
            logical_address: 0,
            payload: Vec::new(),
            working_counter,
            expected_working_counter: expected_wkc,
        };
        FieldbusController::verify_ethercat_lrw(&frame)
            .map(|()| true)
            .map_err(failure)
    }
}
