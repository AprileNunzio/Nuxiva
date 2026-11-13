import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { ALERTS, parseObservability } from './observabilityApi';

const LANGS = ['it', 'en', 'fr', 'es'] as const;
const dictionary = (lang: string): Record<string, string> =>
  (JSON.parse(readFileSync(resolve(__dirname, `../language/${lang}.json`), 'utf8')) as { dictionary: Record<string, string> }).dictionary;

describe('observability parser', () => {
  it('keeps only bounded numbers, known modes and known alerts', () => {
    const parsed = parseObservability({
      squad: { agents: 12, workers: -3, tools: 'x', busy: 1e30 },
      engine: { mode: 'hack', available: true, compared: 5, matched: 5, mismatched: 0, errors: 0, drift: 7 },
      memory: { loaded: true, persons: 3, present: 1, version: 9, approx_bytes: 2048, name: 'Anna' },
      alerts: ['decision_drift', 'unknown', 42],
    });
    expect(parsed.squad).toEqual({ agents: 12, workers: 0, tools: 0, busy: 1e12 });
    expect(parsed.engine.mode).toBe('shadow');
    expect(parsed.engine.drift).toBe(1);
    expect(parsed.alerts).toEqual(['decision_drift']);
    expect(JSON.stringify(parsed)).not.toContain('Anna');
  });

  it('survives hostile payloads', () => {
    for (const raw of [null, 5, 'x', [], { squad: null, engine: [], memory: 'm', alerts: 'a' }]) {
      const parsed = parseObservability(raw);
      expect(parsed.alerts).toEqual([]);
      expect(parsed.memory.loaded).toBe(false);
    }
  });
});

describe('observability language keys', () => {
  it('has identical memory keys in the four languages, including every alert and mode', () => {
    const keys = LANGS.map((lang) =>
      Object.keys(dictionary(lang))
        .filter((k) => k.startsWith('memory_'))
        .sort(),
    );
    for (const set of keys) {
      expect(set).toEqual(keys[0]);
    }
    const reference = new Set(keys[0]);
    for (const alert of ALERTS) {
      expect(reference.has(`memory_alert_${alert}`)).toBe(true);
    }
    for (const mode of ['python', 'shadow', 'rust']) {
      expect(reference.has(`memory_mode_${mode}`)).toBe(true);
    }
  });
});
