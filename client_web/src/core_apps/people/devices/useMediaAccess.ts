import { useCallback, useEffect, useRef, useState } from 'react';
import { secureContextReady } from './secureOrigin';

export type MediaKind = 'camera' | 'microphone';
export type AccessState = 'checking' | 'prompt' | 'granted' | 'denied' | 'insecure' | 'unsupported' | 'missing' | 'busy' | 'failed';

export interface MediaDeviceOption {
  readonly id: string;
  readonly label: string;
  readonly index: number;
}

interface Access {
  readonly state: AccessState;
  readonly stream: MediaStream | null;
  readonly devices: readonly MediaDeviceOption[];
  readonly deviceId: string;
  readonly request: (deviceId?: string) => Promise<MediaStream | null>;
  readonly release: () => void;
}

const INPUT: Record<MediaKind, MediaDeviceKind> = { camera: 'videoinput', microphone: 'audioinput' };

function constraints(kind: MediaKind, deviceId: string): MediaStreamConstraints {
  const pick = deviceId ? { deviceId: { exact: deviceId } } : {};
  return kind === 'camera'
    ? { video: { ...pick, width: { ideal: 1280 }, height: { ideal: 960 } }, audio: false }
    : { audio: { ...pick, channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true }, video: false };
}

function classify(cause: unknown): AccessState {
  const name = cause instanceof DOMException ? cause.name : '';
  if (name === 'NotAllowedError' || name === 'SecurityError' || name === 'PermissionDeniedError') {
    return 'denied';
  }
  if (name === 'NotFoundError' || name === 'OverconstrainedError' || name === 'DevicesNotFoundError') {
    return 'missing';
  }
  if (name === 'NotReadableError' || name === 'TrackStartError' || name === 'AbortError') {
    return 'busy';
  }
  return 'failed';
}

function supported(): boolean {
  return typeof navigator !== 'undefined' && typeof navigator.mediaDevices?.getUserMedia === 'function';
}

export function useMediaAccess(kind: MediaKind): Access {
  const [state, setState] = useState<AccessState>('checking');
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [devices, setDevices] = useState<readonly MediaDeviceOption[]>([]);
  const [deviceId, setDeviceId] = useState('');
  const live = useRef<MediaStream | null>(null);

  const release = useCallback(() => {
    live.current?.getTracks().forEach((track) => track.stop());
    live.current = null;
    setStream(null);
  }, []);

  const listDevices = useCallback(async () => {
    const all = await navigator.mediaDevices.enumerateDevices();
    setDevices(all.filter((d) => d.kind === INPUT[kind]).map((d, i) => ({ id: d.deviceId, label: d.label, index: i + 1 })));
  }, [kind]);

  useEffect(() => {
    if (!secureContextReady()) {
      setState('insecure');
      return undefined;
    }
    if (!supported()) {
      setState('unsupported');
      return undefined;
    }
    let status: PermissionStatus | null = null;
    let cancelled = false;
    const apply = () => {
      if (!cancelled && status && !live.current) {
        setState(status.state === 'granted' ? 'granted' : status.state === 'denied' ? 'denied' : 'prompt');
      }
    };
    navigator.permissions
      ?.query({ name: kind as PermissionName })
      .then((result) => {
        status = result;
        result.addEventListener('change', apply);
        apply();
      })
      .catch(() => !cancelled && setState('prompt'));
    if (!navigator.permissions) {
      setState('prompt');
    }
    return () => {
      cancelled = true;
      status?.removeEventListener('change', apply);
    };
  }, [kind]);

  useEffect(() => release, [release]);

  const request = useCallback(
    async (wanted?: string) => {
      if (!secureContextReady() || !supported()) {
        setState(secureContextReady() ? 'unsupported' : 'insecure');
        return null;
      }
      release();
      const chosen = wanted ?? deviceId;
      try {
        const next = await navigator.mediaDevices.getUserMedia(constraints(kind, chosen));
        live.current = next;
        setStream(next);
        setDeviceId(chosen);
        setState('granted');
        await listDevices();
        return next;
      } catch (cause: unknown) {
        setState(classify(cause));
        return null;
      }
    },
    [deviceId, kind, listDevices, release],
  );

  return { state, stream, devices, deviceId, request, release };
}
