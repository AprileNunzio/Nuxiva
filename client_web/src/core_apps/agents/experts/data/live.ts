import { asRecord, asString, asStringList } from '../../../../node_apps/shared/data/http';

const num = (value: unknown): number | null => (typeof value === 'number' && Number.isFinite(value) ? value : null);
const list = (value: unknown): unknown[] => (Array.isArray(value) ? value : []);

export interface DebianLive {
  readonly kind: 'debian';
  readonly os: string;
  readonly kernel: string;
  readonly host: string;
  readonly uptime: number;
  readonly load: readonly number[];
  readonly cpus: number;
  readonly memory: { readonly total: number; readonly used: number };
  readonly disk: { readonly total: number; readonly used: number };
  readonly temperature: number | null;
  readonly failed: readonly string[] | null;
  readonly updates: { readonly count: number; readonly security: number; readonly packages: readonly string[] } | null;
}

export interface MatchSide {
  readonly name: string;
  readonly abbr: string;
  readonly color: string;
  readonly score: number | null;
}

export interface Match {
  readonly id: string;
  readonly league: string;
  readonly state: 'pre' | 'in' | 'post';
  readonly clock: string;
  readonly start: string;
  readonly home: MatchSide;
  readonly away: MatchSide;
}

export interface FootballLive {
  readonly kind: 'football';
  readonly matches: readonly Match[];
  readonly available: boolean;
}

export interface Activity {
  readonly doing: string;
  readonly recent: readonly { readonly at: number; readonly text: string; readonly kind: string }[];
}

export interface LiveSnapshot {
  readonly activity: Activity;
  readonly data: DebianLive | FootballLive | null;
}

const pair = (value: unknown) => {
  const r = asRecord(value);
  return { total: num(r.total) ?? 0, used: num(r.used) ?? 0 };
};

function side(value: unknown): MatchSide {
  const s = asRecord(value);
  const color = asString(s.color, 6) ?? '';
  return { name: asString(s.short, 30) ?? asString(s.name, 60) ?? '', abbr: asString(s.abbr, 5) ?? '', color: /^[0-9a-f]{6}$/i.test(color) ? `#${color}` : '#29e0ff', score: num(s.score) };
}

function match(value: unknown): Match | null {
  const m = asRecord(value);
  const id = asString(m.id, 20);
  const state = asString(m.state, 4);
  if (!id || (state !== 'pre' && state !== 'in' && state !== 'post')) {
    return null;
  }
  return { id, league: asString(m.league_name, 40) ?? '', state, clock: asString(m.clock, 10) ?? '', start: asString(m.start, 30) ?? '', home: side(m.home), away: side(m.away) };
}

function debian(d: Record<string, unknown>): DebianLive {
  const updates = d.updates === null ? null : asRecord(d.updates);
  return {
    kind: 'debian',
    os: asString(d.os, 80) ?? '',
    kernel: asString(d.kernel, 60) ?? '',
    host: asString(d.host, 60) ?? '',
    uptime: num(d.uptime_s) ?? 0,
    load: list(d.load).map(num).filter((v): v is number => v !== null).slice(0, 3),
    cpus: num(d.cpus) ?? 0,
    memory: pair(d.memory),
    disk: pair(d.disk),
    temperature: num(d.temperature),
    failed: d.failed_units === null ? null : asStringList(d.failed_units, 20),
    updates: updates ? { count: num(updates.count) ?? 0, security: num(updates.security) ?? 0, packages: asStringList(updates.packages, 30) } : null,
  };
}

export function parseLive(value: unknown): LiveSnapshot {
  const raw = asRecord(value);
  const doing = asRecord(raw.doing);
  const activity: Activity = {
    doing: asString(doing.what, 200) ?? '',
    recent: list(raw.recent)
      .map(asRecord)
      .map((m) => ({ at: num(m.at) ?? 0, text: asString(m.text, 400) ?? '', kind: asString(m.kind, 20) ?? '' }))
      .filter((m) => m.text)
      .slice(-8),
  };
  const data = asRecord(raw.data);
  if (data.kind === 'debian') {
    return { activity, data: debian(data) };
  }
  if (data.kind === 'football') {
    return { activity, data: { kind: 'football', matches: list(data.matches).map(match).filter((m): m is Match => m !== null), available: data.available !== false } };
  }
  return { activity, data: null };
}
