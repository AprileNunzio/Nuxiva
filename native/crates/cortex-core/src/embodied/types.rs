use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct HumanoidJoint {
    pub id: String,
    pub angle_rad: f64,
    pub min_angle_rad: f64,
    pub max_angle_rad: f64,
    pub velocity_rad_s: f64,
    pub torque_nm: f64,
    pub max_torque_nm: f64,
    pub temperature_c: f64,
    pub max_temperature_c: f64,
    pub calibration_gain: f64,
    pub prediction_error_ema: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ImuBalanceState {
    pub roll_deg: f64,
    pub pitch_deg: f64,
    pub com_height_m: f64,
    pub zmp_margin_m: f64,
    pub support_polygon_radius_m: f64,
    pub surface_friction_est: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MotorCommand {
    pub joint_id: String,
    pub target_angle_rad: f64,
    pub feedforward_torque_nm: f64,
    pub dt_sec: f64,
    pub measured_load_kg: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ActiveInferenceStep {
    pub joint_id: String,
    pub predicted_angle_rad: f64,
    pub actual_angle_rad: f64,
    pub applied_torque_nm: f64,
    pub free_energy_surprise: f64,
    pub updated_calibration_gain: f64,
    pub zmp_stability_margin_m: f64,
    pub reflex_engaged: bool,
    pub status_key: String,
}
