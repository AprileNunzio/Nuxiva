import { afterEach, describe, expect, it, vi } from 'vitest';
import { deleteVoiceTurn, fetchVoiceAudio, fetchVoiceTurns } from './api';

afterEach(() => vi.unstubAllGlobals());

describe('voice api', () => {
  it('refuses forged identifiers before any request', async () => {
    const spy = vi.fn();
    vi.stubGlobal('fetch', spy);
    await expect(deleteVoiceTurn('../../etc/passwd')).rejects.toThrow('invalid_turn_id');
    await expect(fetchVoiceAudio('ABC')).rejects.toThrow('invalid_turn_id');
    expect(spy).not.toHaveBeenCalled();
  });

  it('builds a bounded query and surfaces server errors', async () => {
    const spy = vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: 'voice_log_unavailable' }), { status: 503 }));
    vi.stubGlobal('fetch', spy);
    await expect(fetchVoiceTurns({ channel: 'voice', q: 'x'.repeat(300), before: 10 })).rejects.toThrow('voice_log_unavailable');
    const url = new URL(String(spy.mock.calls[0][0]), 'http://h');
    expect(url.pathname).toBe('/api/ai_studio/voice/turns');
    expect(url.searchParams.get('q')).toHaveLength(120);
    expect(url.searchParams.get('before')).toBe('10');
  });

  it('rejects non audio payloads', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('<html>', { headers: { 'Content-Type': 'text/html' } })));
    await expect(fetchVoiceAudio('0123456789abcdef')).rejects.toThrow('invalid_audio');
  });
});
