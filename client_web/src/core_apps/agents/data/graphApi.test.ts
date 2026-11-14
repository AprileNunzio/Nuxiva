import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { EXPLORE_MODES, parseExplore, parseGraph } from './graphApi';

const LANGS = ['it', 'en', 'fr', 'es'] as const;
const dictionary = (lang: string): Record<string, string> =>
  (JSON.parse(readFileSync(resolve(__dirname, `../language/${lang}.json`), 'utf8')) as { dictionary: Record<string, string> }).dictionary;

describe('graph parser', () => {
  it('bounds numbers and strips unknown fields', () => {
    const parsed = parseGraph({
      graph: { available: true, files: 12, packages: -4, symbols: 'x', edges: 1e30, secret: 'x' },
      plan: { at: 5, done: 1, steps: [{ id: 's1', agent: 'meteo', intent: 'forecast', goal: 'g', outcome: 'ok', extra: 1 }] },
      consultations: [{ at: 1, who: 'pannello', tool: 'graph_locate', target: 'a.rs', ok: true, ms: 3, token: 'z' }],
      shadow: { persistent: true, totals: { compared: 9, mismatched: 0, errors: 0 }, gate: { observed_days: 2, clean_days: 2, window_mismatches: 0, streak: 9, ready: false } },
    });
    expect(parsed.graph).toEqual({ available: true, files: 12, packages: 0, symbols: 0, sections: 0, edges: 1e12, skipped: 0 });
    expect(parsed.plan?.steps[0]).toEqual({ id: 's1', agent: 'meteo', intent: 'forecast', goal: 'g', outcome: 'ok' });
    expect(parsed.shadow.gate.streak).toBe(9);
    expect(JSON.stringify(parsed)).not.toContain('token');
    expect(JSON.stringify(parsed)).not.toContain('secret');
  });

  it('survives hostile payloads', () => {
    for (const raw of [null, 5, 'x', [], { graph: null, plan: 7, consultations: 'a', shadow: [] }]) {
      const parsed = parseGraph(raw);
      expect(parsed.graph.available).toBe(false);
      expect(parsed.consultations).toEqual([]);
      expect(parsed.shadow.gate.ready).toBe(false);
    }
  });

  it('caps long lists', () => {
    const parsed = parseGraph({ consultations: Array.from({ length: 900 }, () => ({ at: 1, who: 'a', tool: 't', target: 'x', ok: true, ms: 1 })) });
    expect(parsed.consultations.length).toBe(200);
  });

  it('parses explore results defensively', () => {
    expect(parseExplore({ ok: true, items: [{ name: 'f', path: 'a.rs', line: 3, depth: 1, via: 'calls', kind: 'symbol' }], truncated: true }).items).toHaveLength(1);
    expect(parseExplore(null)).toEqual({ ok: false, error: '', items: [], truncated: false });
  });
});

describe('graph translations', () => {
  it('defines every key in all four languages', () => {
    const keys = [
      'graph_title', 'graph_map', 'graph_unavailable', 'graph_plan', 'graph_explore', 'graph_log', 'graph_shadow', 'graph_search',
      ...EXPLORE_MODES.map((m) => `graph_mode_${m}`),
    ];
    for (const lang of LANGS) {
      const dict = dictionary(lang);
      for (const key of keys) expect(dict[key], `${lang}:${key}`).toBeTruthy();
    }
    const base = Object.keys(dictionary('en')).filter((k) => k.startsWith('graph_')).sort();
    for (const lang of LANGS) expect(Object.keys(dictionary(lang)).filter((k) => k.startsWith('graph_')).sort()).toEqual(base);
  });
});
