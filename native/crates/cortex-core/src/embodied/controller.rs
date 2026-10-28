use serde::{Deserialize, Serialize};

use crate::embodied::physics::{
    enforce_safety_envelope, predict_next_angle, simulate_physical_plant,
    update_sensorimotor_plasticity, validate_command,
};
use crate::embodied::types::{ActiveInferenceStep, HumanoidJoint, ImuBalanceState, MotorCommand};
use crate::platform::error::{CortexError, CortexResult};
use crate::platform::sanitizer::sanitize_identifier;

const MAX_SNAPSHOT_LEN: usize = 16_777_216;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EmbodiedCortex {
    joints: Vec<HumanoidJoint>,
    imu: ImuBalanceState,
    total_cycles: u64,
}

impl Default for EmbodiedCortex {
    fn default() -> Self {
        Self::new()
    }
}

impl EmbodiedCortex {
    #[must_use]
    pub fn new() -> Self {
        let joints = vec![
            HumanoidJoint {
                id: "hip_pitch_l".to_string(),
                angle_rad: 0.05,
                min_angle_rad: -1.57,
                max_angle_rad: 1.57,
                velocity_rad_s: 0.0,
                torque_nm: 12.0,
                max_torque_nm: 140.0,
                temperature_c: 34.5,
                max_temperature_c: 85.0,
                calibration_gain: 1.0,
                prediction_error_ema: 0.012,
            },
            HumanoidJoint {
                id: "knee_pitch_l".to_string(),
                angle_rad: 0.12,
                min_angle_rad: 0.0,
                max_angle_rad: 2.35,
                velocity_rad_s: 0.0,
                torque_nm: 18.5,
                max_torque_nm: 160.0,
                temperature_c: 36.0,
                max_temperature_c: 85.0,
                calibration_gain: 1.0,
                prediction_error_ema: 0.010,
            },
            HumanoidJoint {
                id: "ankle_roll_l".to_string(),
                angle_rad: 0.0,
                min_angle_rad: -0.78,
                max_angle_rad: 0.78,
                velocity_rad_s: 0.0,
                torque_nm: 6.0,
                max_torque_nm: 75.0,
                temperature_c: 33.0,
                max_temperature_c: 80.0,
                calibration_gain: 1.0,
                prediction_error_ema: 0.008,
            },
            HumanoidJoint {
                id: "shoulder_pitch_r".to_string(),
                angle_rad: 0.20,
                min_angle_rad: -2.10,
                max_angle_rad: 2.10,
                velocity_rad_s: 0.0,
                torque_nm: 8.0,
                max_torque_nm: 95.0,
                temperature_c: 35.0,
                max_temperature_c: 82.0,
                calibration_gain: 1.0,
                prediction_error_ema: 0.014,
            },
            HumanoidJoint {
                id: "elbow_pitch_r".to_string(),
                angle_rad: 0.45,
                min_angle_rad: 0.0,
                max_angle_rad: 2.40,
                velocity_rad_s: 0.0,
                torque_nm: 5.5,
                max_torque_nm: 65.0,
                temperature_c: 34.0,
                max_temperature_c: 80.0,
                calibration_gain: 1.0,
                prediction_error_ema: 0.009,
            },
            HumanoidJoint {
                id: "torso_yaw".to_string(),
                angle_rad: 0.0,
                min_angle_rad: -1.20,
                max_angle_rad: 1.20,
                velocity_rad_s: 0.0,
                torque_nm: 10.0,
                max_torque_nm: 120.0,
                temperature_c: 35.2,
                max_temperature_c: 85.0,
                calibration_gain: 1.0,
                prediction_error_ema: 0.007,
            },
        ];
        let imu = ImuBalanceState {
            roll_deg: 0.4,
            pitch_deg: 1.1,
            com_height_m: 0.88,
            zmp_margin_m: 0.092,
            support_polygon_radius_m: 0.120,
            surface_friction_est: 0.85,
        };
        Self {
            joints,
            imu,
            total_cycles: 0,
        }
    }

    #[must_use]
    pub fn joints(&self) -> &[HumanoidJoint] {
        &self.joints
    }

    #[must_use]
    pub const fn imu(&self) -> &ImuBalanceState {
        &self.imu
    }

    #[must_use]
    pub const fn total_cycles(&self) -> u64 {
        self.total_cycles
    }

    pub fn step_active_inference(
        &mut self,
        cmd: &MotorCommand,
        measured_angle_override: Option<f64>,
    ) -> CortexResult<ActiveInferenceStep> {
        let clean_joint_id = sanitize_identifier(&cmd.joint_id)?;
        validate_command(cmd)?;
        let idx = self
            .joints
            .iter()
            .position(|j| j.id == clean_joint_id)
            .ok_or(CortexError::UnknownJoint)?;

        let joint_snapshot = self
            .joints
            .get(idx)
            .cloned()
            .ok_or(CortexError::UnknownJoint)?;

        enforce_safety_envelope(&joint_snapshot, &self.imu, cmd)?;

        let predicted = predict_next_angle(&joint_snapshot, cmd);
        let actual = match measured_angle_override {
            Some(val) if val.is_finite() => {
                val.clamp(joint_snapshot.min_angle_rad, joint_snapshot.max_angle_rad)
            }
            _ => simulate_physical_plant(&joint_snapshot, cmd),
        };

        let joint_mut = self.joints.get_mut(idx).ok_or(CortexError::UnknownJoint)?;

        let surprise =
            update_sensorimotor_plasticity(joint_mut, &mut self.imu, cmd, predicted, actual);
        let updated_gain = joint_mut.calibration_gain;
        self.total_cycles = self.total_cycles.saturating_add(1);

        let reflex_engaged = self.imu.zmp_margin_m < 0.035 || surprise > 0.15;
        let status_key = if reflex_engaged {
            "status_reflex_stabilization_active"
        } else {
            "status_active_inference_converged"
        };

        Ok(ActiveInferenceStep {
            joint_id: clean_joint_id,
            predicted_angle_rad: (predicted * 10_000.0).round() / 10_000.0,
            actual_angle_rad: (actual * 10_000.0).round() / 10_000.0,
            applied_torque_nm: cmd.feedforward_torque_nm,
            free_energy_surprise: surprise,
            updated_calibration_gain: (updated_gain * 10_000.0).round() / 10_000.0,
            zmp_stability_margin_m: (self.imu.zmp_margin_m * 10_000.0).round() / 10_000.0,
            reflex_engaged,
            status_key: status_key.to_string(),
        })
    }

    pub fn snapshot_json(&self) -> CortexResult<String> {
        serde_json::to_string(self).map_err(|_| CortexError::SnapshotInvalid)
    }

    pub fn from_snapshot_json(snapshot: &str) -> CortexResult<Self> {
        if snapshot.is_empty() || snapshot.len() > MAX_SNAPSHOT_LEN {
            return Err(CortexError::SnapshotInvalid);
        }
        serde_json::from_str(snapshot).map_err(|_| CortexError::SnapshotInvalid)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn active_inference_step_updates_joint_and_rejects_limit_violation() {
        let mut cortex = EmbodiedCortex::new();
        let valid_cmd = MotorCommand {
            joint_id: "hip_pitch_l".to_string(),
            target_angle_rad: 0.30,
            feedforward_torque_nm: 20.0,
            dt_sec: 0.02,
            measured_load_kg: 1.5,
        };
        assert!(cortex.step_active_inference(&valid_cmd, None).is_ok());

        let invalid_cmd = MotorCommand {
            joint_id: "hip_pitch_l".to_string(),
            target_angle_rad: 2.90,
            feedforward_torque_nm: 20.0,
            dt_sec: 0.02,
            measured_load_kg: 1.5,
        };
        assert_eq!(
            cortex.step_active_inference(&invalid_cmd, None),
            Err(CortexError::JointLimitExceeded)
        );
    }
}
