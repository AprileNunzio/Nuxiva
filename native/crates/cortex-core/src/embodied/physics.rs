use crate::embodied::types::{HumanoidJoint, ImuBalanceState, MotorCommand};
use crate::platform::error::{CortexError, CortexResult};

const GRAVITY_M_S2: f64 = 9.80665;
const MIN_DT: f64 = 0.0005;
const MAX_DT: f64 = 1.0;
const LEARNING_RATE: f64 = 0.12;

pub fn validate_command(cmd: &MotorCommand) -> CortexResult<()> {
    if !cmd.target_angle_rad.is_finite()
        || !cmd.feedforward_torque_nm.is_finite()
        || !cmd.dt_sec.is_finite()
        || !cmd.measured_load_kg.is_finite()
    {
        return Err(CortexError::InvalidExpression);
    }
    if !(MIN_DT..=MAX_DT).contains(&cmd.dt_sec) || cmd.measured_load_kg < 0.0 {
        return Err(CortexError::SafetyEnvelopeViolation);
    }
    Ok(())
}

pub fn enforce_safety_envelope(
    joint: &HumanoidJoint,
    imu: &ImuBalanceState,
    cmd: &MotorCommand,
) -> CortexResult<()> {
    if joint.temperature_c >= joint.max_temperature_c {
        return Err(CortexError::ThermalLimitExceeded);
    }
    if cmd.target_angle_rad < joint.min_angle_rad || cmd.target_angle_rad > joint.max_angle_rad {
        return Err(CortexError::JointLimitExceeded);
    }
    if cmd.feedforward_torque_nm.abs() > joint.max_torque_nm {
        return Err(CortexError::SafetyEnvelopeViolation);
    }
    if imu.roll_deg.abs() > 38.0 || imu.pitch_deg.abs() > 38.0 || imu.zmp_margin_m <= 0.005 {
        return Err(CortexError::BalanceInstability);
    }
    Ok(())
}

#[must_use]
pub fn predict_next_angle(joint: &HumanoidJoint, cmd: &MotorCommand) -> f64 {
    let angle_delta = cmd.target_angle_rad - joint.angle_rad;
    let effective_gain = joint.calibration_gain.clamp(0.25, 2.5);
    let torque_assist = (cmd.feedforward_torque_nm / joint.max_torque_nm.max(1.0)) * 0.15;
    let step_ratio = (cmd.dt_sec * 8.0 * effective_gain).clamp(0.05, 1.0);
    joint.angle_rad + angle_delta * step_ratio + torque_assist * cmd.dt_sec
}

#[must_use]
pub fn simulate_physical_plant(joint: &HumanoidJoint, cmd: &MotorCommand) -> f64 {
    let inertia_damping = 1.0 / (1.0 + 0.08 * cmd.measured_load_kg);
    let gravity_sag = (GRAVITY_M_S2 * 0.0015 * cmd.measured_load_kg) * cmd.target_angle_rad.sin();
    let step_ratio = (cmd.dt_sec * 7.2 * inertia_damping).clamp(0.04, 0.98);
    let raw = joint.angle_rad + (cmd.target_angle_rad - joint.angle_rad) * step_ratio - gravity_sag;
    raw.clamp(joint.min_angle_rad, joint.max_angle_rad)
}

pub fn update_sensorimotor_plasticity(
    joint: &mut HumanoidJoint,
    imu: &mut ImuBalanceState,
    cmd: &MotorCommand,
    predicted_angle: f64,
    actual_angle: f64,
) -> f64 {
    let error = actual_angle - predicted_angle;
    let surprise = error.abs();
    joint.prediction_error_ema = 0.75 * joint.prediction_error_ema + 0.25 * surprise;

    let direction = if (cmd.target_angle_rad - joint.angle_rad).abs() > 1e-6 {
        error / (cmd.target_angle_rad - joint.angle_rad)
    } else {
        0.0
    };
    let gain_delta = (direction * LEARNING_RATE).clamp(-0.08, 0.08);
    joint.calibration_gain = (joint.calibration_gain + gain_delta).clamp(0.35, 2.20);
    joint.velocity_rad_s = (actual_angle - joint.angle_rad) / cmd.dt_sec;
    joint.angle_rad = actual_angle;
    joint.torque_nm = cmd.feedforward_torque_nm;
    joint.temperature_c = (joint.temperature_c + cmd.feedforward_torque_nm.abs() * 0.003)
        .min(joint.max_temperature_c);

    let load_shift = cmd.measured_load_kg * 0.0012 * actual_angle.abs();
    imu.zmp_margin_m =
        (imu.support_polygon_radius_m - load_shift).clamp(0.01, imu.support_polygon_radius_m);
    imu.pitch_deg = (imu.pitch_deg * 0.85 + actual_angle.to_degrees() * 0.05).clamp(-35.0, 35.0);

    (surprise * 1_000_000.0).round() / 1_000_000.0
}
