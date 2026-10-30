import { useCallback, useEffect, useRef, useState } from 'react';
import { LevelSample, meterUrl, parseLevel } from '../data/micTestApi';

export type MeterStatus = 'off' | 'connecting' | 'live' | 'error';

export interface MicMeterController {
  readonly status: MeterStatus;
  readonly level: LevelSample | null;
  readonly peakHoldDb: number;
  readonly error: string | null;
  readonly start: () => void;
  readonly stop: () => void;
}

const MAX_FRAME = 512;
const HOLD_DECAY_DB = 0.6;
const KNOWN_ERRORS = new Set(['mic_busy', 'mic_unavailable', 'mic_stalled', 'mic_closed']);

export function useMicMeter(): MicMeterController {
  const [status, setStatus] = useState<MeterStatus>('off');
  const [level, setLevel] = useState<LevelSample | null>(null);
  const [peakHoldDb, setPeakHoldDb] = useState(-90);
  const [error, setError] = useState<string | null>(null);
  const socket = useRef<WebSocket | null>(null);

  const stop = useCallback(() => {
    const current = socket.current;
    socket.current = null;
    current?.close(1000);
    setStatus('off');
    setLevel(null);
    setPeakHoldDb(-90);
  }, []);

  const start = useCallback(() => {
    socket.current?.close(1000);
    setError(null);
    setStatus('connecting');
    const ws = new WebSocket(meterUrl());
    socket.current = ws;
    let opened = false;
    let failed = false;
    ws.onmessage = (event: MessageEvent) => {
      if (socket.current !== ws || typeof event.data !== 'string' || event.data.length > MAX_FRAME) {
        return;
      }
      let message: Record<string, unknown>;
      try {
        message = JSON.parse(event.data) as Record<string, unknown>;
      } catch {
        return;
      }
      if (message.type === 'ready') {
        opened = true;
        setStatus('live');
      } else if (message.type === 'level') {
        const sample = parseLevel(message);
        setLevel(sample);
        setPeakHoldDb((hold) => Math.max(sample.peakDb, hold - HOLD_DECAY_DB));
      } else if (message.type === 'error') {
        const code = typeof message.code === 'string' && KNOWN_ERRORS.has(message.code) ? message.code : 'mic_unavailable';
        failed = true;
        setError(code);
        setStatus('error');
      } else if (message.type === 'timeout') {
        setStatus('off');
      }
    };
    ws.onclose = () => {
      if (socket.current !== ws) {
        return;
      }
      socket.current = null;
      setLevel(null);
      if (failed) {
        return;
      }
      if (!opened) {
        setError('meter_closed');
        setStatus('error');
        return;
      }
      setStatus('off');
    };
  }, []);

  useEffect(() => () => socket.current?.close(1000), []);

  return { status, level, peakHoldDb, error, start, stop };
}
