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

export interface EpistemicHypothesis {
  readonly id: string;
  readonly label: string;
  readonly prior_probability: number;
  readonly predicted_outcome: string;
  readonly action_plan: string;
}

export interface EpistemicConfrontationRecord {
  readonly id: string;
  readonly context_key: string;
  readonly uncertainty_entropy: number;
  readonly hypotheses: readonly EpistemicHypothesis[];
  readonly chosen_hypothesis_id: string | null;
  readonly user_justification: string | null;
  readonly resolved_certainty: number;
  readonly encrypted_digest: string;
  readonly created_at_epoch_ms: number;
  readonly resolved_at_epoch_ms: number | null;
}

export interface OntologicalAxiom {
  readonly id: string;
  readonly statement: string;
  readonly conservation_law: string;
  readonly is_consistent: boolean;
}

export interface AxiomaticFormalism {
  readonly id: string;
  readonly paradigm: 'calculus' | 'riemann_metric' | 'lie_algebra' | 'symplectic_geometry' | 'discrete_topology';
  readonly name: string;
  readonly differential_operator: string;
  readonly invariance_group: string;
  readonly axioms: readonly OntologicalAxiom[];
  readonly empirical_residual_reduction: number;
  readonly compiled_o1_shortcut: boolean;
}

export interface HumanParityMetrics {
  readonly current_level_percentage: number;
  readonly autonomous_self_learning: boolean;
  readonly embodied_anchoring_moravec: boolean;
  readonly doubt_certainty_alignment: number;
}

export interface PhysicalEmbodimentInfo {
  readonly degrees_of_freedom: number;
  readonly fieldbus_protocol: string;
  readonly supported_bus_modes: readonly string[];
}

export interface EmbodiedCortexOverview {
  readonly columns: readonly CorticalColumnSpec[];
  readonly shortcuts: readonly InvariantShortcut[];
  readonly joints: readonly HumanoidJoint[];
  readonly imu: ImuBalanceState;
  readonly totalCycles: number;
  readonly confrontation: {
    readonly pending_count: number;
    readonly resolved_count: number;
    readonly pending: readonly EpistemicConfrontationRecord[];
    readonly resolved: readonly EpistemicConfrontationRecord[];
  };
  readonly ontological_creativity: {
    readonly invented_formalisms_count: number;
    readonly formalisms: readonly AxiomaticFormalism[];
  };
  readonly physical_embodiment: PhysicalEmbodimentInfo;
  readonly human_parity_metrics: HumanParityMetrics;
}
