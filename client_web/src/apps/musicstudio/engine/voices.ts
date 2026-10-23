import type { VoiceParams } from '../types';

interface Osc {
  readonly type: OscillatorType;
  readonly gain: number;
  readonly detune: number;
  readonly octave: number;
}

const hz = (midi: number) => 440 * Math.pow(2, (midi - 69) / 12);
const num = (v: unknown, fallback: number) => (typeof v === 'number' && Number.isFinite(v) ? v : fallback);
const obj = (v: unknown): Record<string, unknown> => (typeof v === 'object' && v !== null ? (v as Record<string, unknown>) : {});

const noiseCache = new WeakMap<BaseAudioContext, AudioBuffer>();
const noise = (ctx: BaseAudioContext) => {
  const cached = noiseCache.get(ctx);
  if (cached) return cached;
  const buffer = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate);
  const data = buffer.getChannelData(0);
  for (let i = 0; i < data.length; i += 1) data[i] = Math.random() * 2 - 1;
  noiseCache.set(ctx, buffer);
  return buffer;
};

const noiseSource = (ctx: BaseAudioContext, when: number) => {
  const src = ctx.createBufferSource();
  src.buffer = noise(ctx);
  src.loop = true;
  src.loopStart = Math.random() * 1.5;
  src.start(when, src.loopStart);
  return src;
};

export const playSynth = (ctx: BaseAudioContext, dest: AudioNode, voice: VoiceParams, midi: number, when: number, dur: number, vel: number): void => {
  const env = obj(voice.env);
  const filter = obj(voice.filter);
  const a = Math.max(0.001, num(env.a, 0.01));
  const d = Math.max(0.01, num(env.d, 0.2));
  const s = Math.min(1, Math.max(0, num(env.s, 0.6)));
  const r = Math.max(0.02, num(env.r, 0.2));
  const peak = Math.min(1, Math.max(0.02, vel)) * 0.32;
  const hold = Math.max(a + 0.01, dur);
  const end = when + hold + r;
  const amp = ctx.createGain();
  amp.gain.setValueAtTime(0, when);
  amp.gain.linearRampToValueAtTime(peak, when + a);
  amp.gain.linearRampToValueAtTime(peak * s, when + a + d);
  amp.gain.setValueAtTime(peak * s, Math.max(when + a + d, when + hold));
  amp.gain.linearRampToValueAtTime(0, end);
  const lp = ctx.createBiquadFilter();
  lp.type = 'lowpass';
  const cutoff = Math.min(num(filter.cutoff, 8000), ctx.sampleRate / 2.2);
  const sweep = num(filter.env, 0);
  lp.frequency.setValueAtTime(Math.min(cutoff + sweep, ctx.sampleRate / 2.2), when);
  lp.frequency.exponentialRampToValueAtTime(Math.max(60, cutoff), when + a + d + 0.05);
  lp.Q.value = num(filter.q, 0.7);
  lp.connect(amp).connect(dest);
  const oscs = (Array.isArray(voice.oscs) ? voice.oscs : []) as Osc[];
  const vibrato = obj(voice.vibrato);
  const stops: AudioScheduledSourceNode[] = [];
  for (const o of oscs.slice(0, 6)) {
    const osc = ctx.createOscillator();
    osc.type = o.type;
    osc.frequency.value = hz(midi + 12 * num(o.octave, 0));
    osc.detune.value = num(o.detune, 0);
    const g = ctx.createGain();
    g.gain.value = Math.min(1.5, Math.max(0, num(o.gain, 1))) / Math.max(1, oscs.length * 0.7);
    osc.connect(g).connect(lp);
    if (num(vibrato.cents, 0) > 0) {
      const lfo = ctx.createOscillator();
      const depth = ctx.createGain();
      lfo.frequency.value = num(vibrato.rate, 5);
      depth.gain.setValueAtTime(0, when);
      depth.gain.linearRampToValueAtTime(num(vibrato.cents, 0), when + num(vibrato.delay, 0.15) + 0.2);
      lfo.connect(depth).connect(osc.detune);
      lfo.start(when);
      lfo.stop(end + 0.05);
    }
    osc.start(when);
    osc.stop(end + 0.05);
    stops.push(osc);
  }
  const breath = num(voice.breath, 0);
  if (breath > 0) {
    const src = noiseSource(ctx, when);
    const bp = ctx.createBiquadFilter();
    bp.type = 'bandpass';
    bp.frequency.value = Math.min(hz(midi) * 3, 6000);
    bp.Q.value = 0.8;
    const g = ctx.createGain();
    g.gain.value = breath * 0.6;
    src.connect(bp).connect(g).connect(lp);
    src.stop(end + 0.05);
  }
};

export const playDrum = (ctx: BaseAudioContext, dest: AudioNode, voice: VoiceParams, lane: string, when: number, vel: number): void => {
  const level = Math.min(1, Math.max(0.05, vel));
  const tone = num(voice.tone, 0.5);
  const grit = num(voice.grit, 0.1);
  const out = ctx.createGain();
  out.connect(dest);
  const hit = (type: OscillatorType, from: number, to: number, time: number, gain: number) => {
    const osc = ctx.createOscillator();
    const g = ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(from, when);
    osc.frequency.exponentialRampToValueAtTime(Math.max(20, to), when + time);
    g.gain.setValueAtTime(gain * level, when);
    g.gain.exponentialRampToValueAtTime(0.001, when + time);
    osc.connect(g).connect(out);
    osc.start(when);
    osc.stop(when + time + 0.02);
  };
  const burst = (kind: BiquadFilterType, freq: number, time: number, gain: number, q = 0.7) => {
    const src = noiseSource(ctx, when);
    const f = ctx.createBiquadFilter();
    const g = ctx.createGain();
    f.type = kind;
    f.frequency.value = freq;
    f.Q.value = q;
    g.gain.setValueAtTime(gain * level, when);
    g.gain.exponentialRampToValueAtTime(0.001, when + time);
    src.connect(f).connect(g).connect(out);
    src.stop(when + time + 0.02);
  };
  const body = num(voice.kick, 52);
  const snare = num(voice.snare, 190);
  const hat = num(voice.hat, 7600);
  const punch = num(voice.punch, 0.8);
  const snap = num(voice.snap, 0.7);
  switch (lane) {
    case 'kick':
      hit('sine', body * 3.2, body, 0.32 + punch * 0.18, 1.0);
      burst('lowpass', 900, 0.03, 0.4 * punch);
      break;
    case 'snare':
      hit('triangle', snare * 1.4, snare, 0.14, 0.55);
      burst('highpass', 1800 + tone * 1800, 0.18 + grit * 0.1, 0.55 * snap + 0.2);
      break;
    case 'rim':
      hit('square', 1700, 900, 0.03, 0.35);
      break;
    case 'clap':
      for (let i = 0; i < 3; i += 1) {
        const t = when + i * 0.012;
        const src = noiseSource(ctx, t);
        const f = ctx.createBiquadFilter();
        const g = ctx.createGain();
        f.type = 'bandpass';
        f.frequency.value = 1500;
        f.Q.value = 1.1;
        g.gain.setValueAtTime(0.5 * level, t);
        g.gain.exponentialRampToValueAtTime(0.001, t + (i === 2 ? 0.16 : 0.02));
        src.connect(f).connect(g).connect(out);
        src.stop(t + 0.2);
      }
      break;
    case 'hat':
      burst('highpass', hat, 0.05, 0.28);
      break;
    case 'open_hat':
      burst('highpass', hat * 0.9, 0.3, 0.26);
      break;
    case 'tom':
      hit('sine', 190, 110, 0.28, 0.8);
      break;
    case 'crash':
      burst('highpass', 3200, 1.1, 0.34);
      break;
    case 'ride':
      burst('bandpass', 7000, 0.45, 0.2, 2);
      hit('triangle', 5200, 5100, 0.2, 0.08);
      break;
    case 'cowbell':
      hit('square', 810, 800, 0.2, 0.22);
      hit('square', 540, 530, 0.2, 0.22);
      break;
    case 'shaker':
      burst('highpass', 6000, 0.07, 0.2);
      break;
    case 'conga':
      hit('sine', 330, 230, 0.2, 0.7);
      break;
    case 'bongo':
      hit('sine', 480, 360, 0.12, 0.65);
      break;
    case 'clave':
      hit('sine', 2500, 2400, 0.06, 0.6);
      break;
    case 'tamb':
      burst('highpass', 8000, 0.1, 0.25);
      hit('triangle', 4000, 3800, 0.05, 0.1);
      break;
    default:
      burst('bandpass', 2400, 0.1, 0.25, 1.4);
  }
};

export const playRiser = (ctx: BaseAudioContext, dest: AudioNode, when: number, dur: number, vel: number): void => {
  const src = noiseSource(ctx, when);
  const f = ctx.createBiquadFilter();
  const g = ctx.createGain();
  f.type = 'bandpass';
  f.Q.value = 1.4;
  f.frequency.setValueAtTime(400, when);
  f.frequency.exponentialRampToValueAtTime(9000, when + dur);
  g.gain.setValueAtTime(0.001, when);
  g.gain.exponentialRampToValueAtTime(0.35 * vel, when + dur);
  g.gain.linearRampToValueAtTime(0, when + dur + 0.1);
  src.connect(f).connect(g).connect(dest);
  src.stop(when + dur + 0.15);
};
