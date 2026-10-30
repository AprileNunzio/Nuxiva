import { describe, expect, it } from 'vitest';
import { bytes, compactNumber, matches, parseAmount, share } from './format';

describe('format helpers', () => {
  it('parses budget amounts strictly', () => {
    expect(parseAmount('')).toBeNull();
    expect(parseAmount('1.000.000')).toBe(1_000_000);
    expect(parseAmount("2'500")).toBe(2500);
    expect(parseAmount('0')).toBeUndefined();
    expect(parseAmount('-5')).toBeUndefined();
    expect(parseAmount('1e9')).toBeUndefined();
    expect(parseAmount('99999999999999')).toBeUndefined();
  });

  it('computes bounded shares', () => {
    expect(share(50, 100)).toBe(0.5);
    expect(share(500, 100)).toBe(1);
    expect(share(5, null)).toBeNull();
    expect(share(5, 0)).toBeNull();
  });

  it('formats numbers and sizes', () => {
    expect(compactNumber(1500, 'en')).toBe('1.5K');
    expect(compactNumber(-3, 'en')).toBe('0');
    expect(bytes(2_500_000_000)).toBe('2.5 GB');
    expect(bytes(10)).toBe('1 MB');
  });

  it('matches case-insensitive queries', () => {
    expect(matches('', 'x')).toBe(true);
    expect(matches('GPT', 'openai', 'gpt-5')).toBe(true);
    expect(matches('zzz', 'openai')).toBe(false);
  });
});
