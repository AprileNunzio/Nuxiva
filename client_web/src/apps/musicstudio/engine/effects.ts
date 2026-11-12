import type { Effect } from '../types';

export interface Fx {
  readonly input: AudioNode;
  readonly output: AudioNode;
  update(params: Readonly<Record<string, number>>, beat: number): void;
  dispose(): void;
}

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

const mixer = (ctx: BaseAudioContext) => {
  const input = ctx.createGain();
  const output = ctx.createGain();
  const dry = ctx.createGain();
  const wet = ctx.createGain();
  input.connect(dry).connect(output);
  wet.connect(output);
  const setMix = (m: number) => {
    const x = clamp(m, 0, 1);
    dry.gain.value = Math.cos(x * Math.PI * 0.5);
    wet.gain.value = Math.sin(x * Math.PI * 0.5);
  };
  return { input, output, wet, setMix };
};

const lfo = (ctx: BaseAudioContext, rate: number, depth: number, target: AudioParam) => {
  const osc = ctx.createOscillator();
  const amount = ctx.createGain();
  osc.frequency.value = rate;
  amount.gain.value = depth;
  osc.connect(amount).connect(target);
  osc.start();
  return { osc, amount };
};

const impulse = (ctx: BaseAudioContext, seconds: number, damp: number) => {
  const length = Math.max(1, Math.floor(ctx.sampleRate * seconds));
  const buffer = ctx.createBuffer(2, length, ctx.sampleRate);
  for (let c = 0; c < 2; c += 1) {
    const data = buffer.getChannelData(c);
    let last = 0;
    for (let i = 0; i < length; i += 1) {
      const raw = (Math.random() * 2 - 1) * Math.pow(1 - i / length, 2.4);
      last += (raw - last) * (1 - damp * 0.9);
      data[i] = last;
    }
  }
  return buffer;
};

const curve = (drive: number) => {
  const n = 1024;
  const out = new Float32Array(n);
  const k = 1 + drive * 60;
  for (let i = 0; i < n; i += 1) {
    const x = (i / (n - 1)) * 2 - 1;
    out[i] = Math.tanh(k * x) / Math.tanh(k);
  }
  return out;
};

const quantizer = (bits: number) => {
  const n = 2048;
  const out = new Float32Array(n);
  const steps = Math.pow(2, clamp(bits, 2, 16));
  for (let i = 0; i < n; i += 1) out[i] = Math.round(((i / (n - 1)) * 2 - 1) * steps * 0.5) / (steps * 0.5);
  return out;
};

type Builder = (ctx: BaseAudioContext, p: Readonly<Record<string, number>>, beat: number) => Fx;

const BUILDERS: Record<string, Builder> = {
  eq3: (ctx, p) => {
    const low = ctx.createBiquadFilter();
    const mid = ctx.createBiquadFilter();
    const high = ctx.createBiquadFilter();
    low.type = 'lowshelf';
    low.frequency.value = 220;
    mid.type = 'peaking';
    mid.frequency.value = 1400;
    mid.Q.value = 0.8;
    high.type = 'highshelf';
    high.frequency.value = 5200;
    low.connect(mid).connect(high);
    const update = (q: Readonly<Record<string, number>>) => {
      low.gain.value = q.low ?? 0;
      mid.gain.value = q.mid ?? 0;
      high.gain.value = q.high ?? 0;
    };
    update(p);
    return { input: low, output: high, update, dispose: () => [low, mid, high].forEach((n) => n.disconnect()) };
  },
  filter: (ctx, p) => {
    const f = ctx.createBiquadFilter();
    const update = (q: Readonly<Record<string, number>>) => {
      const t = Math.round(q.type ?? 0);
      f.type = t === 1 ? 'highpass' : t === 2 ? 'bandpass' : 'lowpass';
      f.frequency.value = clamp(q.cutoff ?? 8000, 20, ctx.sampleRate / 2.2);
      f.Q.value = clamp(q.q ?? 0.9, 0.1, 18);
    };
    update(p);
    return { input: f, output: f, update, dispose: () => f.disconnect() };
  },
  delay: (ctx, p, beat) => {
    const m = mixer(ctx);
    const d = ctx.createDelay(4);
    const fb = ctx.createGain();
    m.input.connect(d);
    d.connect(fb).connect(d);
    d.connect(m.wet);
    const update = (q: Readonly<Record<string, number>>, b: number) => {
      d.delayTime.value = clamp((q.time ?? 0.375) * b, 0.01, 3.9);
      fb.gain.value = clamp(q.feedback ?? 0.35, 0, 0.92);
      m.setMix(q.mix ?? 0.25);
    };
    update(p, beat);
    return { input: m.input, output: m.output, update, dispose: () => [m.input, m.output, d, fb].forEach((n) => n.disconnect()) };
  },
  reverb: (ctx, p) => {
    const m = mixer(ctx);
    const conv = ctx.createConvolver();
    m.input.connect(conv).connect(m.wet);
    let key = '';
    const update = (q: Readonly<Record<string, number>>) => {
      const next = `${(q.size ?? 2.2).toFixed(2)}|${(q.damp ?? 0.4).toFixed(2)}`;
      if (next !== key) {
        key = next;
        conv.buffer = impulse(ctx, clamp(q.size ?? 2.2, 0.2, 6), clamp(q.damp ?? 0.4, 0, 1));
      }
      m.setMix(q.mix ?? 0.25);
    };
    update(p);
    return { input: m.input, output: m.output, update, dispose: () => [m.input, m.output, conv].forEach((n) => n.disconnect()) };
  },
  chorus: (ctx, p) => {
    const m = mixer(ctx);
    const d = ctx.createDelay(0.1);
    d.delayTime.value = 0.022;
    m.input.connect(d).connect(m.wet);
    const l = lfo(ctx, p.rate ?? 0.8, 0.004, d.delayTime);
    const update = (q: Readonly<Record<string, number>>) => {
      l.osc.frequency.value = q.rate ?? 0.8;
      l.amount.gain.value = 0.002 + (q.depth ?? 0.5) * 0.008;
      m.setMix(q.mix ?? 0.4);
    };
    update(p);
    return { input: m.input, output: m.output, update, dispose: () => { l.osc.stop(); [m.input, m.output, d].forEach((n) => n.disconnect()); } };
  },
  distortion: (ctx, p) => {
    const m = mixer(ctx);
    const shaper = ctx.createWaveShaper();
    shaper.oversample = '4x';
    const tone = ctx.createBiquadFilter();
    tone.type = 'lowpass';
    m.input.connect(shaper).connect(tone).connect(m.wet);
    const update = (q: Readonly<Record<string, number>>) => {
      shaper.curve = curve(clamp(q.drive ?? 0.4, 0, 1));
      tone.frequency.value = 600 + clamp(q.tone ?? 0.6, 0, 1) * 9400;
      m.setMix(q.mix ?? 0.5);
    };
    update(p);
    return { input: m.input, output: m.output, update, dispose: () => [m.input, m.output, shaper, tone].forEach((n) => n.disconnect()) };
  },
  compressor: (ctx, p) => {
    const c = ctx.createDynamicsCompressor();
    const update = (q: Readonly<Record<string, number>>) => {
      c.threshold.value = q.threshold ?? -18;
      c.ratio.value = q.ratio ?? 4;
      c.attack.value = q.attack ?? 0.01;
      c.release.value = q.release ?? 0.2;
    };
    update(p);
    return { input: c, output: c, update, dispose: () => c.disconnect() };
  },
  tremolo: (ctx, p) => {
    const g = ctx.createGain();
    const l = lfo(ctx, p.rate ?? 5, 0.25, g.gain);
    const update = (q: Readonly<Record<string, number>>) => {
      const depth = clamp(q.depth ?? 0.5, 0, 1);
      g.gain.value = 1 - depth * 0.5;
      l.amount.gain.value = depth * 0.5;
      l.osc.frequency.value = q.rate ?? 5;
    };
    update(p);
    return { input: g, output: g, update, dispose: () => { l.osc.stop(); g.disconnect(); } };
  },
  flanger: (ctx, p) => {
    const m = mixer(ctx);
    const d = ctx.createDelay(0.05);
    const fb = ctx.createGain();
    d.delayTime.value = 0.004;
    m.input.connect(d);
    d.connect(fb).connect(d);
    d.connect(m.wet);
    const l = lfo(ctx, p.rate ?? 0.3, 0.003, d.delayTime);
    const update = (q: Readonly<Record<string, number>>) => {
      l.osc.frequency.value = q.rate ?? 0.3;
      l.amount.gain.value = 0.0005 + (q.depth ?? 0.6) * 0.003;
      fb.gain.value = clamp(q.feedback ?? 0.4, 0, 0.9);
      m.setMix(q.mix ?? 0.5);
    };
    update(p);
    return { input: m.input, output: m.output, update, dispose: () => { l.osc.stop(); [m.input, m.output, d, fb].forEach((n) => n.disconnect()); } };
  },
  bitcrusher: (ctx, p) => {
    const m = mixer(ctx);
    const shaper = ctx.createWaveShaper();
    const lp = ctx.createBiquadFilter();
    lp.type = 'lowpass';
    m.input.connect(shaper).connect(lp).connect(m.wet);
    const update = (q: Readonly<Record<string, number>>) => {
      shaper.curve = quantizer(q.bits ?? 8);
      lp.frequency.value = clamp(ctx.sampleRate * 0.5 * (q.rate ?? 0.5), 400, ctx.sampleRate * 0.45);
      m.setMix(q.mix ?? 0.6);
    };
    update(p);
    return { input: m.input, output: m.output, update, dispose: () => [m.input, m.output, shaper, lp].forEach((n) => n.disconnect()) };
  },
  autopan: (ctx, p) => {
    const pan = ctx.createStereoPanner();
    const l = lfo(ctx, p.rate ?? 1, p.depth ?? 0.7, pan.pan);
    const update = (q: Readonly<Record<string, number>>) => {
      l.osc.frequency.value = q.rate ?? 1;
      l.amount.gain.value = clamp(q.depth ?? 0.7, 0, 1);
    };
    update(p);
    return { input: pan, output: pan, update, dispose: () => { l.osc.stop(); pan.disconnect(); } };
  },
  limiter: (ctx, p) => {
    const c = ctx.createDynamicsCompressor();
    c.ratio.value = 20;
    c.attack.value = 0.002;
    c.knee.value = 0;
    const update = (q: Readonly<Record<string, number>>) => {
      c.threshold.value = q.ceiling ?? -1;
      c.release.value = q.release ?? 0.1;
    };
    update(p);
    return { input: c, output: c, update, dispose: () => c.disconnect() };
  },
  phaser: (ctx, p) => {
    const m = mixer(ctx);
    const stages = [0, 1, 2, 3].map(() => {
      const f = ctx.createBiquadFilter();
      f.type = 'allpass';
      f.frequency.value = 800;
      return f;
    });
    m.input.connect(stages[0]);
    for (let i = 0; i < stages.length - 1; i += 1) stages[i].connect(stages[i + 1]);
    stages[3].connect(m.wet);
    const lfos = stages.map((s) => lfo(ctx, p.rate ?? 0.5, 500, s.frequency));
    const update = (q: Readonly<Record<string, number>>) => {
      lfos.forEach((l) => {
        l.osc.frequency.value = q.rate ?? 0.5;
        l.amount.gain.value = 100 + clamp(q.depth ?? 0.6, 0, 1) * 900;
      });
      m.setMix(q.mix ?? 0.5);
    };
    update(p);
    return { input: m.input, output: m.output, update, dispose: () => { lfos.forEach((l) => l.osc.stop()); [m.input, m.output, ...stages].forEach((n) => n.disconnect()); } };
  },
};

export const buildEffect = (ctx: BaseAudioContext, effect: Effect, beat: number): Fx | null => {
  const builder = BUILDERS[effect.type];
  return builder ? builder(ctx, effect.params, beat) : null;
};
