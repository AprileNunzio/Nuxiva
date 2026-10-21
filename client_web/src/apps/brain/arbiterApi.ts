import { getJson, sendJson } from '../shared/http';
import { BrainGlobalDefault, BrainProviderType, BrainTargetConfig } from './types';

export const COMPOSITE_PRESETS = ['NUXIVA_5AXIS', 'A_BALANCED', 'B_QUALITY', 'C_PRODUCTION'] as const;
export type CompositePreset = (typeof COMPOSITE_PRESETS)[number];
export type DecisionPrimitiveType = 'VERDICT' | 'CHOICE' | 'RUBRIC';

export interface LiveArbiterRuntimeContext {
  readonly activeModel: string;
  readonly provider: BrainProviderType;
  readonly baseUrl: string;
  readonly system1Model: string;
  readonly system2Model: string;
}

export function buildLiveArbiterTarget(
  globalDefault: BrainGlobalDefault,
  existing?: BrainTargetConfig
): BrainTargetConfig {
  if (existing && existing.inheritsGlobalDefault === false) {
    return existing;
  }
  let parsedHost = existing?.remoteHost;
  let parsedPort = existing?.remotePort ?? 11434;
  if (globalDefault.provider === 'ollama_remote' && globalDefault.baseUrl) {
    try {
      const parsed = new URL(globalDefault.baseUrl);
      parsedHost = parsed.hostname;
      parsedPort = parsed.port ? Number(parsed.port) : 11434;
    } catch {}
  }
  return {
    id: 'cognitive_arbiter',
    name: existing?.name || 'Arbitro Decisionale Probabilistico',
    roleKey: 'role_cognitive_arbiter',
    descriptionKey: 'desc_cognitive_arbiter',
    category: 'core_brain',
    method: globalDefault.provider,
    providerId:
      globalDefault.provider === 'api_key'
        ? globalDefault.serverId || existing?.providerId
        : existing?.providerId,
    serverId: globalDefault.serverId,
    localMachineId:
      globalDefault.provider === 'ollama_local'
        ? globalDefault.serverId || 'local_workstation'
        : existing?.localMachineId,
    remoteHost: parsedHost,
    remotePort: parsedPort,
    baseUrl: globalDefault.baseUrl,
    assignedModel: globalDefault.modelName,
    temperature: globalDefault.temperature,
    contextWindow: globalDefault.contextWindow,
    status: 'connected',
    latencyMs: existing?.latencyMs ?? 12,
    speedTokensSec: existing?.speedTokensSec ?? 240,
    avatarIcon: 'ShieldCheck',
    accentColor:
      'from-violet-50/80 via-white to-fuchsia-50/40 border-2 border-violet-200 text-violet-800',
    mcpToolsEnabled: globalDefault.mcpToolsEnabled,
    inheritsGlobalDefault: true,
  };
}

export function extractLiveRuntimeContext(
  globalDefault: BrainGlobalDefault,
  targets: readonly BrainTargetConfig[]
): LiveArbiterRuntimeContext {
  const arbiterTarget = targets.find((t) => t.id === 'cognitive_arbiter');
  const fastTarget = targets.find((t) => t.id === 'fast_conversation');
  const reasoningTarget = targets.find((t) => t.id === 'reasoning');

  const activeProvider =
    arbiterTarget && arbiterTarget.inheritsGlobalDefault === false
      ? arbiterTarget.method
      : globalDefault.provider;
  const activeModel =
    arbiterTarget && arbiterTarget.inheritsGlobalDefault === false
      ? arbiterTarget.assignedModel
      : globalDefault.modelName;
  const activeBaseUrl =
    arbiterTarget && arbiterTarget.inheritsGlobalDefault === false
      ? arbiterTarget.baseUrl || globalDefault.baseUrl
      : globalDefault.baseUrl;

  return {
    activeModel,
    provider: activeProvider,
    baseUrl: activeBaseUrl,
    system1Model: fastTarget?.assignedModel || activeModel,
    system2Model: reasoningTarget?.assignedModel || activeModel,
  };
}

export interface ArbiterAxes {
  readonly intelligence: number;
  readonly calibration: number;
  readonly speed: number;
  readonly cost: number;
  readonly securityHomeostasis: number;
}

export interface ArbiterBootstrap {
  readonly mean: number;
  readonly ciLower95: number;
  readonly ciUpper95: number;
}

export interface ArbiterBenchmark {
  readonly datasetHash: string;
  readonly taskCount: number;
  readonly preset: CompositePreset;
  readonly compositeScore: number;
  readonly capabilityScore: number;
  readonly axes: ArbiterAxes;
  readonly ece10Bin: number;
  readonly brierScore: number;
  readonly rpsMean: number;
  readonly paraphraseAgreement: number;
  readonly optionOrderConsistency: number;
  readonly bootstrap: ArbiterBootstrap | null;
}

export interface ArbiterLedger {
  readonly capUsd: number;
  readonly committedUsd: number;
  readonly remainingUsd: number;
  readonly chainIntegrityVerified: boolean;
}

export interface ArbiterConformance {
  readonly passedAll: boolean;
  readonly totalChecks: number;
  readonly passedChecks: number;
  readonly datasetHash: string;
}

export interface ArbiterOverview {
  readonly cascadeThreshold: number;
  readonly benchmark: ArbiterBenchmark;
  readonly conformance: ArbiterConformance;
  readonly ledger: ArbiterLedger;
}

export interface CascadeTestResult {
  readonly selectedTier: string;
  readonly escalated: boolean;
  readonly predictedLabel: string;
  readonly confidence: number;
  readonly conformalLabels: readonly string[];
  readonly totalEntropy: number;
  readonly aleatoricEntropy: number;
  readonly epistemicDisagreement: number;
}

export interface TypedPrimitiveResult {
  readonly primitive: DecisionPrimitiveType;
  readonly predictedLabel: string;
  readonly confidence: number;
  readonly abstained: boolean;
  readonly probabilities: Record<string, number>;
  readonly conformalLabels: readonly string[];
}

function asObj(val: unknown): Record<string, any> {
  return val && typeof val === 'object' ? (val as Record<string, any>) : {};
}

function asNum(val: unknown, fallback = 0): number {
  const n = Number(val);
  return Number.isFinite(n) ? n : fallback;
}

function parseBenchmark(raw: unknown): ArbiterBenchmark {
  const b = asObj(raw);
  const evalObj = asObj(b.evaluation);
  const axes = asObj(evalObj.axes);
  const cal = asObj(b.calibration_details);
  const ci = asObj(evalObj.bootstrap_ci);
  const presetRaw = String(evalObj.preset || 'NUXIVA_5AXIS');
  const preset = COMPOSITE_PRESETS.find((p) => p === presetRaw) ?? 'NUXIVA_5AXIS';
  return {
    datasetHash: String(b.dataset_hash || ''),
    taskCount: asNum(b.task_count, 5),
    preset,
    compositeScore: asNum(evalObj.composite_score),
    capabilityScore: asNum(evalObj.capability_score),
    axes: {
      intelligence: asNum(axes.intelligence),
      calibration: asNum(axes.calibration),
      speed: asNum(axes.speed),
      cost: asNum(axes.cost),
      securityHomeostasis: asNum(axes.security_homeostasis),
    },
    ece10Bin: asNum(cal.ece_10bin),
    brierScore: asNum(cal.brier_score),
    rpsMean: asNum(cal.rps_mean),
    paraphraseAgreement: asNum(cal.paraphrase_agreement, 1),
    optionOrderConsistency: asNum(cal.option_order_consistency, 1),
    bootstrap:
      typeof ci.mean === 'number'
        ? {
            mean: asNum(ci.mean),
            ciLower95: asNum(ci.ci_lower_95),
            ciUpper95: asNum(ci.ci_upper_95),
          }
        : null,
  };
}

export async function fetchArbiterOverview(): Promise<ArbiterOverview> {
  const raw = asObj(await getJson<unknown>('/api/v2/brain/decision-lab'));
  const conf = asObj(raw.conformance);
  const led = asObj(raw.ledger);
  return {
    cascadeThreshold: asNum(raw.cascade_threshold, 0.82),
    benchmark: parseBenchmark(raw.benchmark),
    conformance: {
      passedAll: conf.passed_all !== false,
      totalChecks: asNum(conf.total_checks, 7),
      passedChecks: asNum(conf.passed_checks, 7),
      datasetHash: String(conf.dataset_hash || ''),
    },
    ledger: {
      capUsd: asNum(led.cap_usd, 25),
      committedUsd: asNum(led.committed_usd, 0),
      remainingUsd: asNum(led.remaining_usd, 25),
      chainIntegrityVerified: led.chain_integrity_verified !== false,
    },
  };
}

export async function runArbiterBenchmark(
  preset: CompositePreset,
  runtime: LiveArbiterRuntimeContext
): Promise<ArbiterBenchmark> {
  const raw = await sendJson<unknown>('/api/v2/brain/decision-lab/benchmark', 'POST', {
    preset,
    active_model: runtime.activeModel,
    provider: runtime.provider,
    base_url: runtime.baseUrl,
  });
  return parseBenchmark(raw);
}

export async function saveArbiterThreshold(threshold: number): Promise<number> {
  const raw = asObj(
    await sendJson<unknown>('/api/v2/brain/decision-lab/threshold', 'PUT', { threshold })
  );
  return asNum(raw.cascade_threshold, threshold);
}

export async function simulateArbiterCascade(
  query: string,
  runtime: LiveArbiterRuntimeContext
): Promise<CascadeTestResult> {
  const raw = asObj(
    await sendJson<unknown>('/api/v2/brain/decision-lab/cascade', 'POST', {
      query: query.slice(0, 800),
      active_model: runtime.activeModel,
      provider: runtime.provider,
      base_url: runtime.baseUrl,
      system1_model: runtime.system1Model,
      system2_model: runtime.system2Model,
    })
  );
  const finalDec = asObj(raw.final_decision);
  const conformal = asObj(finalDec.conformal_set);
  const unc = asObj(finalDec.uncertainty);
  const included = Array.isArray(conformal.included_labels)
    ? conformal.included_labels.map((x: unknown) => String(x))
    : [];
  return {
    selectedTier: String(raw.selected_tier || 'system1_fast'),
    escalated: raw.escalated === true,
    predictedLabel: String(finalDec.predicted_label || ''),
    confidence: asNum(finalDec.confidence),
    conformalLabels: included,
    totalEntropy: asNum(unc.total_entropy),
    aleatoricEntropy: asNum(unc.aleatoric_entropy),
    epistemicDisagreement: asNum(unc.epistemic_disagreement),
  };
}

export async function executeTypedPrimitive(payload: {
  primitive: DecisionPrimitiveType;
  query: string;
  temperature: number;
  thresholdTau: number;
  runtime: LiveArbiterRuntimeContext;
}): Promise<TypedPrimitiveResult> {
  const raw = asObj(
    await sendJson<unknown>('/api/v2/brain/decision-lab/decide', 'POST', {
      task_id: `nuxiva_ui_${Date.now()}`,
      primitive: payload.primitive,
      query: payload.query.slice(0, 800),
      proposition: payload.query.slice(0, 500),
      temperature: payload.temperature,
      threshold_tau: payload.thresholdTau,
      active_model: payload.runtime.activeModel,
      provider: payload.runtime.provider,
      base_url: payload.runtime.baseUrl,
    })
  );
  const conformal = asObj(raw.conformal_set);
  const probsObj = asObj(raw.probabilities);
  const cleanProbs: Record<string, number> = {};
  Object.keys(probsObj).forEach((k) => {
    cleanProbs[k] = asNum(probsObj[k]);
  });
  return {
    primitive: payload.primitive,
    predictedLabel: String(raw.predicted_label || ''),
    confidence: asNum(raw.confidence),
    abstained: raw.abstained === true,
    probabilities: cleanProbs,
    conformalLabels: Array.isArray(conformal.included_labels)
      ? conformal.included_labels.map((x: unknown) => String(x))
      : [],
  };
}
