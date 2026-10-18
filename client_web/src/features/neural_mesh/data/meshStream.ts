import { MeshSnapshot, StreamState } from '../domain/types';
import { adminPath } from '../../../shared/http/basePath';
import { TELEMETRY_STREAM_PATH } from './meshApi';
import { TopologyParseError, parseTopology } from './topologyParser';

const MAX_FRAME_BYTES = 2_000_000;
const BASE_BACKOFF_MS = 1000;
const MAX_BACKOFF_MS = 30000;
const OFFLINE_AFTER_ATTEMPTS = 4;

export interface MeshStreamHandlers {
  readonly onSnapshot: (snapshot: MeshSnapshot) => void;
  readonly onState: (state: StreamState) => void;
  readonly onError: (code: string, cause: unknown) => void;
}

function streamUrl(): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}${adminPath(TELEMETRY_STREAM_PATH)}`;
}

export class MeshTelemetryStream {
  private socket: WebSocket | null = null;
  private retryTimer: number | null = null;
  private attempts = 0;
  private stopped = true;

  constructor(private readonly handlers: MeshStreamHandlers) {}

  start(): void {
    this.stopped = false;
    this.connect();
  }

  stop(): void {
    this.stopped = true;
    if (this.retryTimer !== null) {
      window.clearTimeout(this.retryTimer);
      this.retryTimer = null;
    }
    this.socket?.close(1000);
    this.socket = null;
  }

  private connect(): void {
    this.handlers.onState(this.attempts === 0 ? 'connecting' : 'reconnecting');
    const socket = new WebSocket(streamUrl());
    this.socket = socket;
    socket.onopen = () => {
      this.attempts = 0;
      this.handlers.onState('live');
    };
    socket.onmessage = (event: MessageEvent) => this.handleFrame(event.data);
    socket.onclose = () => this.scheduleReconnect();
  }

  private handleFrame(data: unknown): void {
    if (typeof data !== 'string' || data.length > MAX_FRAME_BYTES) {
      this.handlers.onError('telemetry_frame_rejected', new TopologyParseError('telemetry_frame_rejected'));
      return;
    }
    let payload: unknown;
    try {
      payload = JSON.parse(data);
    } catch (cause) {
      this.handlers.onError('telemetry_frame_rejected', cause);
      return;
    }
    try {
      this.handlers.onSnapshot(parseTopology(payload, Date.now()));
    } catch (cause) {
      this.handlers.onError('telemetry_frame_rejected', cause);
    }
  }

  private scheduleReconnect(): void {
    this.socket = null;
    if (this.stopped) {
      return;
    }
    this.attempts += 1;
    this.handlers.onState(this.attempts >= OFFLINE_AFTER_ATTEMPTS ? 'offline' : 'reconnecting');
    const exponential = Math.min(MAX_BACKOFF_MS, BASE_BACKOFF_MS * 2 ** (this.attempts - 1));
    const jitter = Math.random() * exponential * 0.3;
    this.retryTimer = window.setTimeout(() => {
      this.retryTimer = null;
      this.connect();
    }, exponential + jitter);
  }
}
