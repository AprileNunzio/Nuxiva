import { asRecord, asString, requestJson } from '../../shared/data/http';
import { list, num } from './parse';

export const COMPOSITE_PRESETS = ['NUXIVA_5AXIS', 'A_BALANCED', 'B_QUALITY', 'C_PRODUCTION'] as const;
export type CompositePreset = (typeof COMPOSITE_PRESETS)[number];

export interface DecisionLabAxes {
  readonly intelligence: number;
  readonly calibration: number;
  readonly speed: number;
  readonly cost: number;
  readonly securityHomeostasis: number;
}

export interface DecisionLabBootstrap {
  readonly mean: number;
  readonly ciLower95: number;
  readonly ciUpper95: number;
}

export interface DecisionLabBenchmark {
  readonly datasetHash: string;
  readonly taskCount: number;
  readonly preset: CompositePreset;
  readonly compositeScore: number;
  readonly capabilityScore: number;
  readonly axes: DecisionLabAxes;
  readonly ece10Bin: number;
  readonly brierScore: number;
  readonly rpsMean: number;
  readonly paraphraseAgreement: number;
  readonly optionOrderConsistency: number;
  readonly bootstrap: DecisionLabBootstrap | null;
}

export interface DecisionLabLedger {
  readonly capUsd: number;
  readonly committedUsd: number;
  readonly remainingUsd: number;
  readonly chainIntegrityVerified: boolean;
}

export interface DecisionLabConformance {
  readonly passedAll: boolean;
  readonly totalChecks: number;
  readonly passedChecks: number;
  readonly datasetHash: string;
}

export interface DecisionLabOverview {
  readonly cascadeThreshold: number;
  readonly benchmark: DecisionLabBenchmark;
  readonly conformance: DecisionLabConformance;
  readonly ledger: DecisionLabLedger;
}

export interface CascadeSimulationResult {
  readonly selectedTier: string;
  readonly escalated: boolean;
  readonly predictedLabel: string;
  readonly confidence: number;
  readonly conformalLabels: readonly string[];
}

function parseBenchmark(value: unknown): DecisionLabBenchmark {
  const b = asRecord(value);
  const evalObj = asRecord(b.evaluation);
  const axes = asRecord(evalObj.axes);
  const cal = asRecord(b.calibration_details);
  const ci = asRecord(evalObj.bootstrap_ci);
  const presetRaw = asString(evalObj.preset, 40) ?? 'NUXIVA_5AXIS';
  const preset = COMPOSITE_PRESETS.find((p) => p === presetRaw) ?? 'NUXIVA_5AXIS';
  return {
    datasetHash: asString(b.dataset_hash, 120) ?? '',
    taskCount: num(b.task_count),
    preset,
    compositeScore: num(evalObj.composite_score),
    capabilityScore: num(evalObj.capability_score),
    axes: {
      intelligence: num(axes.intelligence),
      calibration: num(axes.calibration),
      speed: num(axes.speed),
      cost: num(axes.cost),
      securityHomeostasis: num(axes.security_homeostasis),
    },
    ece10Bin: num(cal.ece_10bin),
    brierScore: num(cal.brier_score),
    rpsMean: num(cal.rps_mean),
    paraphraseAgreement: num(cal.paraphrase_agreement),
    optionOrderConsistency: num(cal.option_order_consistency),
    bootstrap: typeof ci.mean === 'number' ? {
      mean: num(ci.mean),
      ciLower95: num(ci.ci_lower_95),
      ciUpper95: num(ci.ci_upper_95),
    } : null,
  };
}

export async function fetchDecisionLab(signal?: AbortSignal): Promise<DecisionLabOverview> {
  const raw = asRecord(await requestJson<unknown>('/api/brains/decision-lab', { signal }));
  const conf = asRecord(raw.conformance);
  const led = asRecord(raw.ledger);
  return {
    cascadeThreshold: num(raw.cascade_threshold) || 0.82,
    benchmark: parseBenchmark(raw.benchmark),
    conformance: {
      passedAll: conf.passed_all === true,
      totalChecks: num(conf.total_checks),
      passedChecks: num(conf.passed_checks),
      datasetHash: asString(conf.dataset_hash, 120) ?? '',
    },
    ledger: {
      capUsd: num(led.cap_usd),
      committedUsd: num(led.committed_usd),
      remainingUsd: num(led.remaining_usd),
      chainIntegrityVerified: led.chain_integrity_verified === true,
    },
  };
}

export async function runDecisionBenchmark(preset: CompositePreset): Promise<DecisionLabBenchmark> {
  const raw = await requestJson<unknown>('/api/brains/decision-lab/benchmark', {
    method: 'POST',
    body: JSON.stringify({ preset }),
  });
  return parseBenchmark(raw);
}

export async function updateCascadeThreshold(threshold: number): Promise<number> {
  const raw = asRecord(await requestJson<unknown>('/api/brains/decision-lab/threshold', {
    method: 'PUT',
    body: JSON.stringify({ threshold }),
  }));
  return num(raw.cascade_threshold);
}

export async function simulateCascadeDecision(query: string): Promise<CascadeSimulationResult> {
  const raw = asRecord(await requestJson<unknown>('/api/brains/decision-lab/cascade', {
    method: 'POST',
    body: JSON.stringify({ query: query.slice(0, 800) }),
  }));
  const finalDec = asRecord(raw.final_decision);
  const conformal = asRecord(finalDec.conformal_set);
  return {
    selectedTier: asString(raw.selected_tier, 40) ?? 'system1_fast',
    escalated: raw.escalated === true,
    predictedLabel: asString(finalDec.predicted_label, 120) ?? '',
    confidence: num(finalDec.confidence),
    conformalLabels: list(conformal.included_labels).filter((x): x is string => typeof x === 'string'),
  };
}
