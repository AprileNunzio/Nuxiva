import { afterEach, describe, expect, it, vi } from 'vitest';

afterEach(() => {
  vi.unstubAllGlobals();
  vi.resetModules();
});

describe('live brain sync', () => {
  it('notifies other sources but not the publisher', async () => {
    vi.stubGlobal('window', new EventTarget());
    const { newSourceId, publishBrainChange, subscribeBrainChanges } = await import('./liveSync');
    const me = newSourceId();
    const other = newSourceId();
    expect(me).toMatch(/^[0-9a-f]{16}$/);
    const mine = vi.fn();
    const theirs = vi.fn();
    const stopMine = subscribeBrainChanges(me, mine);
    const stopTheirs = subscribeBrainChanges(other, theirs);
    publishBrainChange(me);
    expect(mine).not.toHaveBeenCalled();
    expect(theirs).toHaveBeenCalledTimes(1);
    stopTheirs();
    publishBrainChange(me);
    expect(theirs).toHaveBeenCalledTimes(1);
    stopMine();
  });

  it('ignores malformed events', async () => {
    vi.stubGlobal('window', new EventTarget());
    const { BRAIN_EVENT, subscribeBrainChanges } = await import('./liveSync');
    const listener = vi.fn();
    const stop = subscribeBrainChanges('x', listener);
    window.dispatchEvent(new CustomEvent(BRAIN_EVENT, { detail: { source: 1 } }));
    expect(listener).not.toHaveBeenCalled();
    stop();
  });
});
