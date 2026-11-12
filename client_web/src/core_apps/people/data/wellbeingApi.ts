import { NodeModuleError, asRecord, asString, requestJson } from '../../../node_apps/shared/data/http';
import { SLUG } from './peopleApi';

export type Area = 'tension' | 'exhaustion' | 'receptive' | 'relief';
export type Stage = 'assessment' | 'treatment' | 'consolidation';
export type Phase = 'opening' | 'central' | 'closing';
export const AREAS: readonly Area[] = ['tension', 'exhaustion', 'receptive', 'relief'];

export interface LiveAffect {
  readonly arousal: number;
  readonly valence: number;
  readonly area: Area;
  readonly browTension: number;
  readonly mimic: number;
  readonly lipTone: number;
  readonly calibrating: boolean;
}

export interface Turn {
  readonly role: 'user' | 'assistant';
  readonly text: string;
}

export interface WellSession {
  readonly id: string;
  readonly stage: Stage;
  readonly phase: Phase;
  readonly turns: readonly Turn[];
}

export interface WellbeingState {
  readonly consent: boolean;
  readonly stage: Stage;
  readonly nextAt: number | null;
  readonly due: boolean;
  readonly concluded: boolean;
  readonly live: LiveAffect | null;
  readonly session: WellSession | null;
}

export interface TurnResult {
  readonly reply: string;
  readonly phase: Phase;
  readonly crisis: boolean;
  readonly nearingEnd: boolean;
}

const slugOf = (slug: string): string => {
  if (!SLUG.test(slug)) {
    throw new NodeModuleError('invalid_person', 400);
  }
  return encodeURIComponent(slug);
};
const base = (slug: string): string => `/api/people/${slugOf(slug)}/wellbeing`;
const list = (value: unknown): unknown[] => (Array.isArray(value) ? value : []);
const num = (value: unknown): number => (typeof value === 'number' && Number.isFinite(value) ? value : 0);
const area = (value: unknown): Area => (AREAS as readonly unknown[]).includes(value) ? (value as Area) : 'receptive';
const stage = (value: unknown): Stage => (['assessment', 'treatment', 'consolidation'].includes(String(value)) ? (value as Stage) : 'assessment');
const phase = (value: unknown): Phase => (['opening', 'central', 'closing'].includes(String(value)) ? (value as Phase) : 'opening');

function session(value: unknown): WellSession | null {
  const raw = asRecord(value);
  const id = asString(raw.id, 32) ?? '';
  if (!/^[a-f0-9]{8,32}$/.test(id)) {
    return null;
  }
  return {
    id,
    stage: stage(raw.stage),
    phase: phase(raw.phase),
    turns: list(raw.turns).map(asRecord).flatMap((t) => (t.role === 'user' || t.role === 'assistant' ? [{ role: t.role, text: asString(t.text, 4000) ?? '' }] : [])),
  };
}

export async function fetchWellbeing(slug: string, signal?: AbortSignal): Promise<WellbeingState> {
  const raw = asRecord(await requestJson<unknown>(base(slug), { signal }));
  const plan = asRecord(raw.plan);
  const live = asRecord(raw.live);
  return {
    consent: raw.consent === true,
    stage: stage(plan.stage),
    nextAt: typeof plan.next_at === 'number' ? plan.next_at : null,
    due: plan.due === true,
    concluded: Number(plan.concluded) === 1,
    live: typeof live.arousal === 'number'
      ? { arousal: num(live.arousal), valence: num(live.valence), area: area(live.area), browTension: num(live.brow_tension), mimic: num(live.mimic), lipTone: num(live.lip_tone), calibrating: live.calibrating === true }
      : null,
    session: session(raw.session),
  };
}

export const setWellbeingConsent = (slug: string, active: boolean) =>
  requestJson<unknown>(`${base(slug)}/consent`, { method: 'PUT', body: JSON.stringify({ active }) });

export async function startSession(slug: string, lang: string, moodBefore: number | null): Promise<WellSession> {
  const created = session(await requestJson<unknown>(`${base(slug)}/sessions`, { method: 'POST', body: JSON.stringify({ lang, mood_before: moodBefore }) }));
  if (!created) {
    throw new NodeModuleError('invalid_session', 502);
  }
  return created;
}

export async function sendTurn(slug: string, sid: string, text: string): Promise<TurnResult> {
  const raw = asRecord(await requestJson<unknown>(`${base(slug)}/sessions/${encodeURIComponent(sid)}/turn`, { method: 'POST', body: JSON.stringify({ text }) }));
  return { reply: asString(raw.reply, 4000) ?? '', phase: phase(raw.phase), crisis: raw.crisis === true, nearingEnd: raw.nearing_end === true };
}

export const closeSession = (slug: string, sid: string, moodAfter: number | null) =>
  requestJson<unknown>(`${base(slug)}/sessions/${encodeURIComponent(sid)}/close`, { method: 'POST', body: JSON.stringify({ mood_after: moodAfter }) });

export const eraseWellbeing = (slug: string) => requestJson<unknown>(base(slug), { method: 'DELETE' });

export async function downloadReport(slug: string, lang: string, transcripts: boolean): Promise<void> {
  const response = await fetch(`${base(slug)}/report?format=md&lang=${encodeURIComponent(lang.slice(0, 2))}&transcripts=${transcripts}`, {
    credentials: 'same-origin',
    headers: { 'X-Nuxiva-Request': '1' },
  });
  if (!response.ok) {
    throw new NodeModuleError('report_failed', response.status);
  }
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement('a');
  link.href = url;
  link.download = `${slug}-wellbeing.md`;
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
