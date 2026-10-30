import { describe, expect, it } from 'vitest';
import { addItem, cloudRef, moveItem, removeItem, sameChain, setPrimary } from './chain';

describe('chain editing', () => {
  it('moves items within bounds only', () => {
    expect(moveItem(['a', 'b', 'c'], 2, -1)).toEqual(['a', 'c', 'b']);
    expect(moveItem(['a', 'b'], 0, -1)).toEqual(['a', 'b']);
    expect(moveItem(['a', 'b'], 1, 1)).toEqual(['a', 'b']);
  });

  it('adds valid unique refs up to the limit', () => {
    expect(addItem(['qwen2.5:7b'], 'cloud:openai/gpt-5')).toEqual(['qwen2.5:7b', 'cloud:openai/gpt-5']);
    expect(addItem(['qwen2.5:7b'], 'qwen2.5:7b')).toEqual(['qwen2.5:7b']);
    expect(addItem([], '<script>')).toEqual([]);
    expect(addItem([], ' ')).toEqual([]);
    const full = Array.from({ length: 12 }, (_, i) => `m${i}`);
    expect(addItem(full, 'extra')).toHaveLength(12);
  });

  it('promotes a ref to primary without duplicates', () => {
    expect(setPrimary(['a', 'b', 'c'], 'c')).toEqual(['c', 'a', 'b']);
    expect(setPrimary(['a'], 'bad ref')).toEqual(['a']);
  });

  it('removes and compares chains', () => {
    expect(removeItem(['a', 'b'], 'a')).toEqual(['b']);
    expect(sameChain(['a', 'b'], ['a', 'b'])).toBe(true);
    expect(sameChain(['a', 'b'], ['b', 'a'])).toBe(false);
  });

  it('builds cloud refs safely', () => {
    expect(cloudRef('openai', 'gpt-5')).toBe('cloud:openai/gpt-5');
    expect(cloudRef('openai', '')).toBeNull();
    expect(cloudRef('bad provider', 'x')).toBeNull();
  });
});
