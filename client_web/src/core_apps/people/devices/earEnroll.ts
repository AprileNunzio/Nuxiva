import { reportError } from '../../../shared/errors/errorBus';

const RATE = 16000;
const CHUNK = 1600;
const WORKLET = 'class NuxivaTap extends AudioWorkletProcessor { process(inputs) { const c = inputs[0] && inputs[0][0]; if (c) this.port.postMessage(c.slice(0)); return true; } } registerProcessor("nuxiva-enroll-tap", NuxivaTap);';

export type EnrollEvent =
  | { readonly type: 'progress'; readonly count: number; readonly ok: boolean }
  | { readonly type: 'level'; readonly value: number }
  | { readonly type: 'unavailable' }
  | { readonly type: 'done'; readonly count: number }
  | { readonly type: 'closed' };

function socketUrl(): string {
  const mounted = window.location.pathname === '/admin' || window.location.pathname.startsWith('/admin/');
  const scheme = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${scheme}//${window.location.host}${mounted ? '/admin' : ''}/ws/ear`;
}

function toInt16(samples: readonly number[]): Int16Array {
  const pcm = new Int16Array(samples.length);
  for (let i = 0; i < samples.length; i += 1) {
    pcm[i] = Math.max(-32768, Math.min(32767, Math.round(samples[i] * 32767)));
  }
  return pcm;
}

function parse(raw: unknown): Record<string, unknown> | null {
  if (typeof raw !== 'string' || raw.length > 65536) {
    return null;
  }
  try {
    const value: unknown = JSON.parse(raw);
    return typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}

export class VoiceEnrollment {
  private socket: WebSocket | null = null;
  private context: AudioContext | null = null;
  private finished = false;

  constructor(private readonly slug: string, private readonly stream: MediaStream, private readonly emit: (event: EnrollEvent) => void) {}

  async start(): Promise<void> {
    const socket = new WebSocket(socketUrl());
    socket.binaryType = 'arraybuffer';
    this.socket = socket;
    socket.onmessage = (message) => this.receive(parse(message.data));
    socket.onclose = () => {
      this.teardown();
      this.emit({ type: 'closed' });
    };
    await new Promise<void>((resolve, reject) => {
      socket.onopen = () => resolve();
      socket.onerror = () => reject(new Error('ear_unreachable'));
    });
    this.send({ type: 'client', page: 'admin_enroll', visible: 'admin', href: window.location.pathname.slice(0, 60) });
    this.send({ type: 'enroll_start', slug: this.slug });
    await this.tap();
  }

  stop(): void {
    if (this.socket?.readyState === WebSocket.OPEN && !this.finished) {
      this.finished = true;
      this.send({ type: 'enroll_stop' });
      window.setTimeout(() => this.socket?.close(), 1500);
    } else {
      this.socket?.close();
    }
    this.teardown();
  }

  private send(payload: Record<string, unknown>): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(payload));
    }
  }

  private receive(data: Record<string, unknown> | null): void {
    if (!data) {
      return;
    }
    const count = Number(data.count ?? 0);
    if (data.type === 'enroll_progress') {
      this.emit({ type: 'progress', count: Number.isFinite(count) ? count : 0, ok: data.ok !== false });
    } else if (data.type === 'enroll_unavailable') {
      this.emit({ type: 'unavailable' });
    } else if (data.type === 'enroll_done') {
      this.emit({ type: 'done', count: Number.isFinite(count) ? count : 0 });
    }
  }

  private async tap(): Promise<void> {
    const context = new AudioContext();
    this.context = context;
    const url = URL.createObjectURL(new Blob([WORKLET], { type: 'application/javascript' }));
    try {
      await context.audioWorklet.addModule(url);
    } finally {
      URL.revokeObjectURL(url);
    }
    const node = new AudioWorkletNode(context, 'nuxiva-enroll-tap');
    context.createMediaStreamSource(this.stream).connect(node);
    const ratio = context.sampleRate / RATE;
    let buffer: number[] = [];
    let position = 0;
    let peak = 0;
    node.port.onmessage = (message: MessageEvent<Float32Array>) => {
      const input = message.data;
      for (; position < input.length; position += ratio) {
        const sample = input[Math.floor(position)];
        buffer.push(sample);
        peak = Math.max(peak, Math.abs(sample));
      }
      position -= input.length;
      if (buffer.length >= CHUNK) {
        if (this.socket?.readyState === WebSocket.OPEN) {
          this.socket.send(toInt16(buffer).buffer);
        }
        this.emit({ type: 'level', value: Math.min(1, peak) });
        buffer = [];
        peak = 0;
      }
    };
  }

  private teardown(): void {
    void this.context?.close().catch((cause: unknown) => reportError('people_voice_failed', cause));
    this.context = null;
  }
}
