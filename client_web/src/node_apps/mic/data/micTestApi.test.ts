import { afterEach, describe, expect, it, vi } from 'vitest';
import { parseLevel, runMicTest } from './micTestApi';

const WAV_HEADER = 'RIFF\u0000\u0000\u0000\u0000WAVEfmt ' + '\u0000'.repeat(32);
const wav = btoa(WAV_HEADER);

function respond(payload: unknown, status = 200) {
  vi.stubGlobal('window', { location: { pathname: '/', protocol: 'http:', host: 'nuxiva.local' } });
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(payload), { status })));
}

afterEach(() => vi.unstubAllGlobals());

describe('mic test api', () => {
  it('clamps level frames and rejects unknown zones', () => {
    expect(parseLevel({ rms_db: -200, peak_db: 5, zone: 'boom' })).toEqual({ rmsDb: -90, peakDb: 0, zone: 'silent' });
    expect(parseLevel({ rms_db: -20, peak_db: -3, zone: 'good' })).toEqual({ rmsDb: -20, peakDb: -3, zone: 'good' });
  });

  it('parses a report and turns both recordings into wav blobs', async () => {
    respond({
      report: { seconds: 5, verdict: 'raise', wake_gain: 6.5, phrase_gain: 12, limits: { wake_gain: 8, max_gain: 30, autotuned: true }, eq: { enabled: true }, timeline: [{ rms_db: -40, peak_db: -30, zone: 'quiet' }] },
      audio: { raw: wav, processed: wav },
    });
    const result = await runMicTest({ seconds: 5 });
    expect(result.report.verdict).toBe('raise');
    expect(result.report.wakeGain).toBe(6.5);
    expect(result.report.autotuned).toBe(true);
    expect(result.report.timeline).toHaveLength(1);
    expect(result.raw.type).toBe('audio/wav');
  });

  it('refuses audio that is not a wav file', async () => {
    respond({ report: {}, audio: { raw: btoa('<script>alert(1)</script>'), processed: wav } });
    await expect(runMicTest({ seconds: 5 })).rejects.toThrow('mictest_audio_invalid');
  });

  it('surfaces the server error code', async () => {
    respond({ detail: 'mic_busy' }, 409);
    await expect(runMicTest({ seconds: 5 })).rejects.toMatchObject({ code: 'mic_busy', status: 409 });
  });
});
