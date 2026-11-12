import { describe, expect, it } from 'vitest';
import { coherent, parsePolicy, parsePrivacy, presetPolicy } from './privacyApi';

describe('privacy api parsing', () => {
  it('accepts only known policies', () => {
    expect(parsePolicy({ profile: 'balanced', personal: 'home', sensitive: 'local' })).toEqual(presetPolicy('balanced'));
    expect(parsePolicy({ profile: 'balanced', personal: 'everywhere', sensitive: 'local' })).toBeNull();
    expect(parsePolicy({ profile: 'root', personal: 'any', sensitive: 'any' })).toBeNull();
  });

  it('falls back to the most protective policy on malformed data', () => {
    const data = parsePrivacy({ default: 'x', people: [{ slug: '../x' }, { slug: 'anna', name: 'Anna', role: 'owner' }] });
    expect(data.policy.sensitive).toBe('local');
    expect(data.people).toEqual([{ slug: 'anna', name: 'Anna', owner: true, policy: null }]);
    expect(data.total.sensitive.blocked).toBe(0);
  });

  it('rejects sensitive rules looser than personal ones', () => {
    expect(coherent({ profile: 'custom', personal: 'local', sensitive: 'any' })).toBe(false);
    expect(coherent({ profile: 'custom', personal: 'any', sensitive: 'home' })).toBe(true);
  });
});
