import { afterEach, describe, expect, it, vi } from 'vitest';
import { parseStreamFrames, streamMessage } from './api';
import { formatThinking } from './thinking';

afterEach(() => vi.unstubAllGlobals());

const sse = (frames: object[], split: number) => {
  const text = frames.map((f) => `data: ${JSON.stringify(f)}\n\n`).join('');
  const bytes = new TextEncoder().encode(text);
  return new ReadableStream<Uint8Array>({
    start(controller) {
      for (let i = 0; i < bytes.length; i += split) controller.enqueue(bytes.slice(i, i + split));
      controller.close();
    },
  });
};

describe('ai studio stream', () => {
  it('keeps incomplete frames for the next chunk', () => {
    const { frames, rest } = parseStreamFrames('data: {"type":"token","token":"a"}\n\ndata: {"type":"tok');
    expect(frames).toEqual([{ type: 'token', token: 'a' }]);
    expect(rest).toBe('data: {"type":"tok');
  });

  it('delivers tokens, resets and the final message across tiny chunks', async () => {
    const message = { id: 'msg_a', content: 'Ciao', thought: 'x', thinking_ms: 1200 };
    const body = sse([
      { type: 'status', state: 'thinking' },
      { type: 'token', token: 'sba' },
      { type: 'reset' },
      { type: 'thought_delta', token: 'x' },
      { type: 'token', token: 'Ci' },
      { type: 'token', token: 'ao' },
      { type: 'done', message },
    ], 7);
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body, { status: 200 })));
    let text = '';
    let thought = '';
    const final = await streamMessage('th_1', 'ciao', [], null, 'fast', {
      onToken: (t) => { text += t; },
      onThoughtDelta: (d) => { thought += d; },
      onReset: () => { text = ''; thought = ''; },
    });
    expect(text).toBe('Ciao');
    expect(thought).toBe('x');
    expect(final).toMatchObject(message);
  });

  it('surfaces server errors from the stream', async () => {
    const body = sse([{ type: 'error', code: 'brain_unavailable', detail: 'down' }], 64);
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body, { status: 200 })));
    await expect(streamMessage('th_1', 'ciao', [], null, 'fast')).rejects.toThrow('brain_unavailable');
  });

  it('formats real thinking time', () => {
    expect(formatThinking(0)).toBeUndefined();
    expect(formatThinking(undefined)).toBeUndefined();
    expect(formatThinking(400)).toBe('1s');
    expect(formatThinking(13_000)).toBe('13s');
    expect(formatThinking(396_000)).toBe('6m 36s');
  });
});
