use std::collections::HashMap;

use crate::embodied::types::HumanoidJoint;
use crate::platform::error::{CortexError, CortexResult};

pub const JOINT_IDS_34: [&str; 34] = [
    "neck_yaw",
    "neck_pitch",
    "neck_roll",
    "torso_yaw",
    "torso_pitch",
    "torso_roll",
    "left_shoulder_pitch",
    "left_shoulder_roll",
    "left_shoulder_yaw",
    "left_elbow_pitch",
    "right_shoulder_pitch",
    "right_shoulder_roll",
    "right_shoulder_yaw",
    "right_elbow_pitch",
    "left_hand_thumb",
    "left_hand_index",
    "left_hand_middle",
    "left_hand_ring",
    "left_hand_pinky",
    "right_hand_thumb",
    "right_hand_index",
    "right_hand_middle",
    "right_hand_ring",
    "right_hand_pinky",
    "left_hip_yaw",
    "left_hip_roll",
    "left_hip_pitch",
    "left_knee_pitch",
    "left_ankle_pitch",
    "right_hip_yaw",
    "right_hip_roll",
    "right_hip_pitch",
    "right_knee_pitch",
    "right_ankle_pitch",
];

#[derive(Debug, Clone)]
pub struct HumanoidKinematics34 {
    joints: HashMap<String, HumanoidJoint>,
}

impl Default for HumanoidKinematics34 {
    fn default() -> Self {
        Self::new()
    }
}

impl HumanoidKinematics34 {
    #[must_use]
    pub fn new() -> Self {
        let mut joints = HashMap::with_capacity(34);
        for id in JOINT_IDS_34 {
            let (min_rad, max_rad, max_torque) = Self::specs_for_joint(id);
            joints.insert(
                id.to_string(),
                HumanoidJoint {
                    id: id.to_string(),
                    angle_rad: 0.0,
                    min_angle_rad: min_rad,
                    max_angle_rad: max_rad,
                    velocity_rad_s: 0.0,
                    torque_nm: 0.0,
                    max_torque_nm: max_torque,
                    temperature_c: 25.0,
                    max_temperature_c: 75.0,
                    calibration_gain: 1.0,
                    prediction_error_ema: 0.0,
                },
            );
        }
        Self { joints }
    }

    fn specs_for_joint(id: &str) -> (f64, f64, f64) {
        if id.starts_with("neck_") {
            (-1.05, 1.05, 15.0)
        } else if id.starts_with("torso_") {
            (-0.78, 0.78, 80.0)
        } else if id.contains("shoulder_") {
            (-2.61, 2.61, 45.0)
        } else if id.contains("elbow_") {
            (-2.35, 0.0, 35.0)
        } else if id.contains("hand_") {
            (-0.1, 1.57, 8.0)
        } else if id.contains("hip_") {
            (-1.57, 1.57, 120.0)
        } else if id.contains("knee_") {
            (0.0, 2.44, 150.0)
        } else if id.contains("ankle_") {
            (-0.78, 0.78, 90.0)
        } else {
            (-1.57, 1.57, 30.0)
        }
    }

    #[must_use]
    pub fn joint_count(&self) -> usize {
        self.joints.len()
    }

    pub fn get_joint(&self, id: &str) -> CortexResult<&HumanoidJoint> {
        self.joints.get(id).ok_or(CortexError::UnknownJoint)
    }

    pub fn enforce_limits(&self, id: &str, target_rad: f64) -> CortexResult<f64> {
        let joint = self.get_joint(id)?;
        if target_rad < joint.min_angle_rad || target_rad > joint.max_angle_rad {
            return Err(CortexError::JointLimitExceeded);
        }
        Ok(target_rad)
    }

    pub fn update_joint(
        &mut self,
        id: &str,
        angle_rad: f64,
        velocity_rad_s: f64,
        torque_nm: f64,
        temperature_c: f64,
    ) -> CortexResult<()> {
        let joint = self.joints.get_mut(id).ok_or(CortexError::UnknownJoint)?;
        if temperature_c > joint.max_temperature_c {
            return Err(CortexError::ThermalLimitExceeded);
        }
        if torque_nm.abs() > joint.max_torque_nm * 1.25 {
            return Err(CortexError::SafetyEnvelopeViolation);
        }
        joint.angle_rad = angle_rad;
        joint.velocity_rad_s = velocity_rad_s;
        joint.torque_nm = torque_nm;
        joint.temperature_c = temperature_c;
        Ok(())
    }

    #[must_use]
    pub fn forward_kinematics_hand(&self, is_right: bool) -> [f64; 3] {
        let prefix = if is_right { "right" } else { "left" };
        let s_pitch = self
            .joints
            .get(&format!("{prefix}_shoulder_pitch"))
            .map_or(0.0, |j| j.angle_rad);
        let s_roll = self
            .joints
            .get(&format!("{prefix}_shoulder_roll"))
            .map_or(0.0, |j| j.angle_rad);
        let e_pitch = self
            .joints
            .get(&format!("{prefix}_elbow_pitch"))
            .map_or(0.0, |j| j.angle_rad);

        let l_upper = 0.28;
        let l_forearm = 0.24;
        let sign = if is_right { 1.0 } else { -1.0 };

        let x = (l_upper * s_pitch.sin() + l_forearm * (s_pitch + e_pitch).sin()) * s_roll.cos();
        let y = sign * (0.18 + l_upper * s_roll.sin());
        let z = 0.55 - (l_upper * s_pitch.cos() + l_forearm * (s_pitch + e_pitch).cos());

        [x, y, z]
    }

    #[must_use]
    pub fn list_all_joints(&self) -> Vec<HumanoidJoint> {
        let mut list = Vec::with_capacity(self.joints.len());
        for id in JOINT_IDS_34 {
            if let Some(j) = self.joints.get(id) {
                list.push(j.clone());
            }
        }
        list
    }
}


#[cfg(test)]
#[allow(clippy::unwrap_used, clippy::float_cmp)]
mod tests {
    use super::*;

    #[test]
    fn test_humanoid_34dof_kinematics() {
        let mut k = HumanoidKinematics34::new();
        assert_eq!(k.joint_count(), 34);

        let enforced = k.enforce_limits("left_shoulder_pitch", 0.5).unwrap();
        assert_eq!(enforced, 0.5);

        assert!(k.enforce_limits("left_elbow_pitch", 1.0).is_err());

        k.update_joint("left_shoulder_pitch", 0.3, 0.1, 10.0, 30.0).unwrap();
        let joint = k.get_joint("left_shoulder_pitch").unwrap();
        assert_eq!(joint.angle_rad, 0.3);

        let pose = k.forward_kinematics_hand(false);
        assert!(pose[2] < 0.6);

        assert!(k.update_joint("left_shoulder_pitch", 0.3, 0.1, 10.0, 80.0).is_err());
    }
}
