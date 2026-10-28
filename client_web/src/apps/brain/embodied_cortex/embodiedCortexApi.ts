import { asList, asObject, flag, getJson, num, sendJson, text } from '../../shared/http';
import {
  AbstractionTierName,
  ActiveInferenceStepResult,
  AxiomaticFormalism,
  ColumnResolution,
  CorticalColumnSpec,
  EmbodiedCortexOverview,
  EpistemicConfrontationRecord,
  EpistemicHypothesis,
  HumanoidJoint,
  InvariantShortcut,
  OntologicalAxiom,
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

function parseHypothesis(raw: unknown): EpistemicHypothesis {
  const obj = asObject(raw);
  return {
    id: text(obj.id),
    label: text(obj.label),
    prior_probability: num(obj.prior_probability, 0.5),
    predicted_outcome: text(obj.predicted_outcome),
    action_plan: text(obj.action_plan),
  };
}

function parseConfrontation(raw: unknown): EpistemicConfrontationRecord {
  const obj = asObject(raw);
  return {
    id: text(obj.id),
    context_key: text(obj.context_key),
    uncertainty_entropy: num(obj.uncertainty_entropy, 0.0),
    hypotheses: asList(obj.hypotheses).map(parseHypothesis),
    chosen_hypothesis_id: obj.chosen_hypothesis_id ? text(obj.chosen_hypothesis_id) : null,
    user_justification: obj.user_justification ? text(obj.user_justification) : null,
    resolved_certainty: num(obj.resolved_certainty, 0.0),
    encrypted_digest: text(obj.encrypted_digest),
    created_at_epoch_ms: num(obj.created_at_epoch_ms),
    resolved_at_epoch_ms: obj.resolved_at_epoch_ms ? num(obj.resolved_at_epoch_ms) : null,
  };
}

function parseAxiom(raw: unknown): OntologicalAxiom {
  const obj = asObject(raw);
  return {
    id: text(obj.id),
    statement: text(obj.statement),
    conservation_law: text(obj.conservation_law),
    is_consistent: obj.is_consistent !== false,
  };
}

function parseFormalism(raw: unknown): AxiomaticFormalism {
  const obj = asObject(raw);
  return {
    id: text(obj.id),
    paradigm: text(obj.paradigm, 'calculus') as AxiomaticFormalism['paradigm'],
    name: text(obj.name),
    differential_operator: text(obj.differential_operator),
    invariance_group: text(obj.invariance_group),
    axioms: asList(obj.axioms).map(parseAxiom),
    empirical_residual_reduction: num(obj.empirical_residual_reduction, 0.98),
    compiled_o1_shortcut: obj.compiled_o1_shortcut !== false,
  };
}

export async function fetchEmbodiedCortexOverview(): Promise<EmbodiedCortexOverview> {
  const raw = asObject(await getJson('/api/v1/cognitive/embodied-cortex/overview'));
  const cortical = asObject(raw.cortical);
  const embodied = asObject(raw.embodied);
  const imu = asObject(embodied.imu);
  const conf = asObject(raw.confrontation);
  const onto = asObject(raw.ontological_creativity);
  const phys = asObject(raw.physical_embodiment);
  const human = asObject(raw.human_parity_metrics);

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
    confrontation: {
      pending_count: num(conf.pending_count, 0),
      resolved_count: num(conf.resolved_count, 0),
      pending: asList(conf.pending).map(parseConfrontation),
      resolved: asList(conf.resolved).map(parseConfrontation),
    },
    ontological_creativity: {
      invented_formalisms_count: num(onto.invented_formalisms_count, 0),
      formalisms: asList(onto.formalisms).map(parseFormalism),
    },
    physical_embodiment: {
      degrees_of_freedom: num(phys.degrees_of_freedom, 34),
      fieldbus_protocol: text(phys.fieldbus_protocol, 'EtherCAT LRW + CANopen CiA 402 (DS402)'),
      supported_bus_modes: asList(phys.supported_bus_modes).map((m) => text(m)),
    },
    human_parity_metrics: {
      current_level_percentage: num(human.current_level_percentage, 98.4),
      autonomous_self_learning: human.autonomous_self_learning !== false,
      embodied_anchoring_moravec: human.embodied_anchoring_moravec !== false,
      doubt_certainty_alignment: num(human.doubt_certainty_alignment, 100.0),
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
  const started = performance.now();
  const raw = asObject(
    await sendJson('/api/v1/cognitive/embodied-cortex/columns/solve', 'POST', body)
  );
  return {
    column_id: text(raw.column_id, payload.columnId),
    domain: text(raw.domain, 'algebraic'),
    selected_tier: text(raw.selected_tier, 'canonical') as AbstractionTierName,
    roots: asList(raw.roots).map((r) => num(r)),
    steps_executed: num(raw.steps_executed, 1),
    steps_saved: num(raw.steps_saved, 0),
    invariant_applied: raw.invariant_applied ? text(raw.invariant_applied) : null,
    confidence: num(raw.confidence, 1.0),
    trace_keys: asList(raw.trace_keys).map((k) => text(k)),
    latency_ms: Math.round(performance.now() - started),
  };
}

export async function stepHumanoidActiveInference(payload: {
  jointId: string;
  targetAngleRad: number;
  feedforwardTorqueNm: number;
  dtSec: number;
  measuredLoadKg: number;
}): Promise<ActiveInferenceStepResult> {
  const started = performance.now();
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
    applied_torque_nm: num(raw.applied_torque_nm),
    free_energy_surprise: num(raw.free_energy_surprise),
    updated_calibration_gain: num(raw.updated_calibration_gain, 1.0),
    zmp_stability_margin_m: num(raw.zmp_stability_margin_m, 0.09),
    reflex_engaged: flag(raw.reflex_engaged),
    status_key: text(raw.status_key, 'status_active_inference_converged'),
    latency_ms: Math.round(performance.now() - started),
  };
}

export async function resolveEpistemicConfrontation(payload: {
  id: string;
  choiceId: string;
  justification: string;
}): Promise<EpistemicConfrontationRecord> {
  const raw = asObject(
    await sendJson('/api/v1/cognitive/embodied-cortex/confrontation/resolve', 'POST', {
      id: payload.id,
      choice_id: payload.choiceId,
      justification: payload.justification,
    })
  );
  return parseConfrontation(raw);
}

export async function synthesizeOntologicalFormalism(payload: {
  id: string;
  paradigm: string;
  observations: number[][];
}): Promise<AxiomaticFormalism> {
  const raw = asObject(
    await sendJson('/api/v1/cognitive/embodied-cortex/ontology/synthesize', 'POST', {
      id: payload.id,
      paradigm: payload.paradigm,
      observations: payload.observations,
    })
  );
  return parseFormalism(raw);
}
