export type AbstractionTierName = 'procedural' | 'canonical' | 'invariant';

export interface CorticalColumnSpec {
  readonly id: string;
  readonly domain: string;
  readonly preferred_tier: AbstractionTierName;
  readonly maturity_score: number;
  readonly total_executions: number;
  readonly shortcuts_consolidated: number;
}

export interface InvariantShortcut {
  readonly id: string;
  readonly pattern_signature: string;
  readonly domain: string;
  readonly coefficient_ratio: number;
  readonly constant_offset: number;
  readonly synaptic_strength: number;
  readonly activations: number;
}

export interface ColumnResolution {
  readonly column_id: string;
  readonly domain: string;
  readonly selected_tier: AbstractionTierName;
  readonly roots: readonly number[];
  readonly steps_executed: number;
  readonly steps_saved: number;
  readonly invariant_applied: string | null;
  readonly confidence: number;
  readonly trace_keys: readonly string[];
  readonly latency_ms: number;
}

export interface HumanoidJoint {
  readonly id: string;
  readonly angle_rad: number;
  readonly min_angle_rad: number;
  readonly max_angle_rad: number;
  readonly velocity_rad_s: number;
  readonly torque_nm: number;
  readonly max_torque_nm: number;
  readonly temperature_c: number;
  readonly max_temperature_c: number;
  readonly calibration_gain: number;
  readonly prediction_error_ema: number;
}

export interface ImuBalanceState {
  readonly roll_deg: number;
  readonly pitch_deg: number;
  readonly com_height_m: number;
  readonly zmp_margin_m: number;
  readonly support_polygon_radius_m: number;
  readonly surface_friction_est: number;
}

export interface ActiveInferenceStepResult {
  readonly joint_id: string;
  readonly predicted_angle_rad: number;
  readonly actual_angle_rad: number;
  readonly applied_torque_nm: number;
  readonly free_energy_surprise: number;
  readonly updated_calibration_gain: number;
  readonly zmp_stability_margin_m: number;
  readonly reflex_engaged: boolean;
  readonly status_key: string;
  readonly latency_ms: number;
}

export interface EmbodiedCortexMetrics {
  readonly cortical_maturity_pct: number;
  readonly embodied_grounding_pct: number;
  readonly estimated_human_logic_pct: number;
  readonly rust_engine_version: string;
}

export interface EmbodiedCortexOverview {
  readonly columns: readonly CorticalColumnSpec[];
  readonly shortcuts: readonly InvariantShortcut[];
  readonly joints: readonly HumanoidJoint[];
  readonly imu: ImuBalanceState;
  readonly totalCycles: number;
  readonly metrics: EmbodiedCortexMetrics;
}
