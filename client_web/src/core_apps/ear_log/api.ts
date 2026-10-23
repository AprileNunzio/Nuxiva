import { asList, asObject, flag, num, sendJson, text } from '../shared/http';
import { EarEntry, EarFilters, EarJournal, EarLive, EarPerson, EarStats, EntryKind, FeedbackInput, Verdict } from './types';

const KINDS: readonly EntryKind[] = ['command', 'heard', 'wake'];
const VERDICTS: readonly Verdict[] = ['', 'ok', 'wrong'];
const MODES = ['auto', 'on', 'off'] as const;
const SLUG = /^[a-z0-9][a-z0-9-]{0,40}$/;
const ID = /^[0-9a-f]{12}$/;

export const journalUrl = (filters: EarFilters): string => {
  const params = new URLSearchParams({ limit: String(Math.max(1, Math.min(200, filters.limit))) });
  if (filters.kind) params.set('kind', filters.kind);
  if (filters.verdict) params.set('verdict', filters.verdict);
  if (filters.speaker) params.set('speaker', filters.speaker);
  if (filters.query.trim()) params.set('q', filters.query.trim().slice(0, 80));
  return `/api/ear/journal?${params.toString()}`;
};

export const audioUrl = (id: string): string => (ID.test(id) ? `/api/ear/journal/${id}/audio` : '');

const entry = (raw: unknown): EarEntry | null => {
  const row = asObject(raw);
  const id = text(row.id);
  const kind = text(row.kind) as EntryKind;
  const verdict = text(row.verdict) as Verdict;
  if (!ID.test(id) || !KINDS.includes(kind)) return null;
  const speaker = text(row.speaker);
  const fix = text(row.fix_speaker);
  return {
    id,
    kind,
    ts: num(row.ts),
    lang: text(row.lang),
    speaker: SLUG.test(speaker) ? speaker : '',
    score: num(row.score),
    live: flag(row.live),
    dur: num(row.dur),
    text: text(row.text),
    audio: flag(row.audio),
    verdict: VERDICTS.includes(verdict) ? verdict : '',
    correction: text(row.correction),
    fixSpeaker: SLUG.test(fix) ? fix : '',
    note: text(row.note),
    applied: flag(row.applied),
  };
};

const live = (raw: unknown): EarLive => {
  const row = asObject(raw);
  const mode = text(row.mode) as EarLive['mode'];
  return {
    available: flag(row.available),
    mode: MODES.includes(mode) ? mode : 'auto',
    active: flag(row.active),
    reason: text(row.reason),
    interval: num(row.interval),
    decodeMs: num(row.decode_ms),
    load: num(row.load),
  };
};

const stats = (raw: unknown): EarStats => {
  const row = asObject(raw);
  return { total: num(row.total), pending: num(row.pending), wrong: num(row.wrong), audioMb: num(row.audio_mb) };
};

const person = (raw: unknown): EarPerson | null => {
  const row = asObject(raw);
  const slug = text(row.slug);
  return SLUG.test(slug) ? { slug, name: text(row.name, slug).slice(0, 80) } : null;
};

export const parseJournal = (raw: unknown): EarJournal => {
  const body = asObject(raw);
  return {
    items: asList(body.items).map(entry).filter((item): item is EarEntry => item !== null),
    stats: stats(body.stats),
    live: live(body.live),
    people: asList(body.people).map(person).filter((item): item is EarPerson => item !== null),
  };
};

export const sendFeedback = (id: string, input: FeedbackInput) =>
  sendJson(`/api/ear/journal/${encodeURIComponent(id)}/feedback`, 'POST', input);
export const deleteEntry = (id: string) => sendJson(`/api/ear/journal/${encodeURIComponent(id)}`, 'DELETE');
export const purgeJournal = () => sendJson('/api/ear/journal/purge', 'POST', {});
