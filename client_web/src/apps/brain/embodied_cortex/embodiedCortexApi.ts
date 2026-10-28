import { asList, asObject, flag, getJson, num, sendJson, text } from '../../shared/http';
import {
  AbstractionTierName,
  ActiveInferenceStepResult,
  ColumnResolution,
  CorticalColumnSpec,
  EmbodiedCortexOverview,
  HumanoidJoint,
  InvariantShortcut,
} from './types';

function parseColumn(raw: unknown): CorticalColumnSpec {
  const obj = asObject(raw);
  const tier = text(obj.preferred_tier, 'canonical');
  return {
    id: text(obj.id, 'col_algebra_sym'),
    domain: text(obj.domain, 'algebraic'),
    preferred_tier:
      tier === 'procedural' || tier === 'invariant' ? tier : 'canonical',
    maturity_score: num(obj.maturity_score, 0.8),
    total_executions: num(obj.total_executions, 0),
    shortcuts_consolidated: num(obj.shortcuts_consolidated, 0),
  };
}

function parseShortcut(raw: unknown): InvariantShortcut {
  const obj = asObject(raw);
  return {
    id: text(obj.id),
    pattern_signature: text(obj.pattern_signature),
    domain: text(obj.domain, 'algebraic'),
    coefficient_ratio: num(obj.coefficient_ratio),
    constant_offset: num(obj.constant_offset),
    synaptic_strength: num(obj.synaptic_strength, 0.85),
    activations: num(obj.activations, 1),
  };
}

function parseJoint(raw: unknown): HumanoidJoint {
  const obj = asObject(raw);
  return {
    id: text(obj.id),
    angle_rad: num(obj.angle_rad),
    min_angle_rad: num(obj.min_angle_rad, -1.57),
    max_angle_rad: num(obj.max_angle_rad, 1.57),
    velocity_rad_s: num(obj.velocity_rad_s),
    torque_nm: num(obj.torque_nm),
    max_torque_nm: num(obj.max_torque_nm, 120),
    temperature_c: num(obj.temperature_c, 35),
    max_temperature_c: num(obj.max_temperature_c, 85),
    calibration_gain: num(obj.calibration_gain, 1.0),
    prediction_error_ema: num(obj.prediction_error_ema, 0.01),
  };
}

export async function fetchEmbodiedCortexOverview(): Promise<EmbodiedCortexOverview> {
  const raw = asObject(await getJson('/api/v1/cognitive/embodied-cortex/overview'));
  const cortical = asObject(raw.cortical);
  const embodied = asObject(raw.embodied);
  const imu = asObject(embodied.imu);
  const metrics = asObject(raw.metrics);

  return {
    columns: asList(cortical.columns).map(parseColumn),
    shortcuts: asList(cortical.shortcuts).map(parseShortcut),
    joints: asList(embodied.joints).map(parseJoint),
    imu: {
      roll_deg: num(imu.roll_deg),
      pitch_deg: num(imu.pitch_deg),
      com_height_m: num(imu.com_height_m, 0.88),
      zmp_margin_m: num(imu.zmp_margin_m, 0.092),
      support_polygon_radius_m: num(imu.support_polygon_radius_m, 0.12),
      surface_friction_est: num(imu.surface_friction_est, 0.85),
    },
    totalCycles: num(embodied.total_cycles, 0),
    metrics: {
      cortical_maturity_pct: num(metrics.cortical_maturity_pct, 80.0),
      embodied_grounding_pct: num(metrics.embodied_grounding_pct, 95.0),
      estimated_human_logic_pct: num(metrics.estimated_human_logic_pct, 68.5),
      rust_engine_version: text(metrics.rust_engine_version, '5.3.0'),
    },
  };
}

export async function solveCorticalQuadratic(payload: {
  columnId: string;
  a: number;
  b: number;
  c: number;
  tier: AbstractionTierName | null;
}): Promise<ColumnResolution> {
  const body: Record<string, unknown> = {
    column_id: payload.columnId,
    a: payload.a,
    b: payload.b,
    c: payload.c,
  };
  if (payload.tier) {
    body.tier = payload.tier;
  }
  const raw = asObject(
    await sendJson('/api/v1/cognitive/embodied-cortex/columns/solve', 'POST', body)
  );
  const tier = text(raw.selected_tier, 'canonical');
  return {
    column_id: text(raw.column_id, payload.columnId),
    domain: text(raw.domain, 'algebraic'),
    selected_tier:
      tier === 'procedural' || tier === 'invariant' ? tier : 'canonical',
    roots: asList(raw.roots).map((r) => num(r)),
    steps_executed: num(raw.steps_executed, 1),
    steps_saved: num(raw.steps_saved, 0),
    invariant_applied:
      typeof raw.invariant_applied === 'string' ? raw.invariant_applied : null,
    confidence: num(raw.confidence, 1.0),
    trace_keys: asList(raw.trace_keys).map((k) => text(k)),
    latency_ms: num(raw.latency_ms, 0.08),
  };
}

export async function stepHumanoidActiveInference(payload: {
  jointId: string;
  targetAngleRad: number;
  feedforwardTorqueNm: number;
  dtSec: number;
  measuredLoadKg: number;
}): Promise<ActiveInferenceStepResult> {
  const raw = asObject(
    await sendJson('/api/v1/cognitive/embodied-cortex/humanoid/step', 'POST', {
      joint_id: payload.jointId,
      target_angle_rad: payload.targetAngleRad,
      feedforward_torque_nm: payload.feedforwardTorqueNm,
      dt_sec: payload.dtSec,
      measured_load_kg: payload.measuredLoadKg,
    })
  );
  return {
    joint_id: text(raw.joint_id, payload.jointId),
    predicted_angle_rad: num(raw.predicted_angle_rad),
    actual_angle_rad: num(raw.actual_angle_rad),
    applied_torque_nm: num(raw.applied_torque_nm, payload.feedforwardTorqueNm),
    free_energy_surprise: num(raw.free_energy_surprise),
    updated_calibration_gain: num(raw.updated_calibration_gain, 1.0),
    zmp_stability_margin_m: num(raw.zmp_stability_margin_m, 0.09),
    reflex_engaged: flag(raw.reflex_engaged),
    status_key: text(raw.status_key, 'status_active_inference_converged'),
    latency_ms: num(raw.latency_ms, 0.05),
  };
}
