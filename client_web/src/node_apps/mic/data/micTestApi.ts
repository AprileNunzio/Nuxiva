import { adminPath } from '../../../shared/http/basePath';
import { asRecord, requestJson } from '../../shared/data/http';

export type LevelZone = 'silent' | 'quiet' | 'good' | 'loud' | 'clip';
export type MicVerdict = 'silent' | 'raise' | 'ok' | 'lower';

export interface LevelSample {
  readonly rmsDb: number;
  readonly peakDb: number;
  readonly zone: LevelZone;
}

export interface EqDraft {
  readonly enabled: boolean;
  readonly highpass_hz: number;
  readonly low_db: number;
  readonly mid_db: number;
  readonly high_db: number;
}

export interface MicTestRequest {
  readonly seconds: number;
  readonly target_rms?: number;
  readonly eq?: EqDraft;
}

export interface MicTestReport {
  readonly seconds: number;
  readonly verdict: MicVerdict;
  readonly peakDb: number;
  readonly voiceDb: number;
  readonly noiseDb: number;
  readonly snrDb: number;
  readonly clipRatio: number;
  readonly voicedRatio: number;
  readonly wakeGain: number;
  readonly wakeGainMedian: number;
  readonly phraseGain: number;
  readonly wakeGainLimit: number;
  readonly maxGain: number;
  readonly autotuned: boolean;
  readonly eqEnabled: boolean;
  readonly timeline: readonly LevelSample[];
}

export interface MicTestResult {
  readonly report: MicTestReport;
  readonly raw: Blob;
  readonly processed: Blob;
}

const ZONES: readonly LevelZone[] = ['silent', 'quiet', 'good', 'loud', 'clip'];
const VERDICTS: readonly MicVerdict[] = ['silent', 'raise', 'ok', 'lower'];
const MAX_AUDIO_B64 = 600_000;
const MAX_TIMELINE = 400;
const BASE64 = /^[A-Za-z0-9+/]+={0,2}$/;
export const METER_PATH = '/api/ear/mictest/meter';

function num(value: unknown, min: number, max: number, fallback = 0): number {
  return typeof value === 'number' && Number.isFinite(value) ? Math.min(max, Math.max(min, value)) : fallback;
}

function pick<T extends string>(value: unknown, allowed: readonly T[], fallback: T): T {
  return typeof value === 'string' && (allowed as readonly string[]).includes(value) ? (value as T) : fallback;
}

export function parseLevel(value: unknown): LevelSample {
  const raw = asRecord(value);
  return { rmsDb: num(raw.rms_db, -90, 0, -90), peakDb: num(raw.peak_db, -90, 0, -90), zone: pick(raw.zone, ZONES, 'silent') };
}

function wavBlob(value: unknown): Blob {
  if (typeof value !== 'string' || value.length > MAX_AUDIO_B64 || !BASE64.test(value)) {
    throw new Error('mictest_audio_invalid');
  }
  const binary = atob(value);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  if (bytes.length < 44 || String.fromCharCode(...bytes.subarray(0, 4)) !== 'RIFF' || String.fromCharCode(...bytes.subarray(8, 12)) !== 'WAVE') {
    throw new Error('mictest_audio_invalid');
  }
  return new Blob([bytes], { type: 'audio/wav' });
}

function parseReport(value: unknown): MicTestReport {
  const raw = asRecord(value);
  const limits = asRecord(raw.limits);
  const timeline = Array.isArray(raw.timeline) ? raw.timeline.slice(0, MAX_TIMELINE).map(parseLevel) : [];
  return {
    seconds: num(raw.seconds, 0, 30),
    verdict: pick(raw.verdict, VERDICTS, 'silent'),
    peakDb: num(raw.peak_db, -90, 0, -90),
    voiceDb: num(raw.voice_db, -90, 0, -90),
    noiseDb: num(raw.noise_db, -90, 0, -90),
    snrDb: num(raw.snr_db, -90, 120),
    clipRatio: num(raw.clip_ratio, 0, 1),
    voicedRatio: num(raw.voiced_ratio, 0, 1),
    wakeGain: num(raw.wake_gain, 0, 100, 1),
    wakeGainMedian: num(raw.wake_gain_median, 0, 100, 1),
    phraseGain: num(raw.phrase_gain, 0, 100, 1),
    wakeGainLimit: num(limits.wake_gain, 0, 100, 1),
    maxGain: num(limits.max_gain, 0, 100, 1),
    autotuned: limits.autotuned === true,
    eqEnabled: asRecord(raw.eq).enabled === true,
    timeline,
  };
}

export async function runMicTest(request: MicTestRequest, signal?: AbortSignal): Promise<MicTestResult> {
  const payload = asRecord(
    await requestJson<unknown>(adminPath('/api/ear/mictest'), { method: 'POST', body: JSON.stringify(request), signal }),
  );
  const audio = asRecord(payload.audio);
  return { report: parseReport(payload.report), raw: wavBlob(audio.raw), processed: wavBlob(audio.processed) };
}

export function meterUrl(): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}${adminPath(METER_PATH)}`;
}
