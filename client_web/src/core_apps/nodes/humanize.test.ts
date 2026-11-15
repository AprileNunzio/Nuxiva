import { describe, expect, it } from 'vitest';
import { componentLabel, groupRepeats, readableId, tierLabel } from './humanize';

const t = (key: string) => `<${key}>`;

describe('humanize', () => {
  it('strips hash prefixes and prettifies ids', () => {
    expect(readableId('078c1579ab54.agency-lab')).toBe('Agency lab');
    expect(readableId('weather_widget')).toBe('Weather widget');
    expect(readableId('...')).toBe('...');
  });

  it('uses translations for known components only', () => {
    expect(componentLabel('nuxiva-core', t)).toBe('<res_name_nuxiva_core>');
    expect(componentLabel('browser', t)).toBe('<res_name_browser>');
    expect(componentLabel('abcdef123456.diorama', t)).toBe('Diorama');
  });

  it('turns tiers into plain words', () => {
    expect(tierLabel('Tier-1 (Compute & Virtual Core)', t)).toBe('<tier_main>');
    expect(tierLabel('Tier-2 (Smart Edge Satellite)', t)).toBe('<tier_edge>');
    expect(tierLabel('Tier-3', t)).toBe('<tier_light>');
    expect(tierLabel('Android', t)).toBe('Android');
    expect(tierLabel(undefined, t)).toBe('');
  });

  it('groups repeated entries keeping order', () => {
    const out = groupRepeats(['a', 'b', 'a', 'a'], (x) => x);
    expect(out).toEqual([{ item: 'a', count: 3 }, { item: 'b', count: 1 }]);
  });
});
