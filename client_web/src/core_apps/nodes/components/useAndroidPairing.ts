import { useCallback, useEffect, useRef, useState } from 'react';
import QRCode from 'qrcode';
import { reportError } from '../../../shared/errors/errorBus';
import { NodeModuleError, requestJson } from '../../../node_apps/shared/data/http';

export interface ApkInfo {
  readonly version: string;
  readonly name: string;
  readonly url: string;
  readonly sha256: string;
}

export interface Pairing {
  readonly id: string;
  readonly link: string;
  readonly code: string;
  readonly expires: number;
  readonly server: string;
  readonly fingerprint: string;
  readonly apk: ApkInfo;
}

export type PairingPhase = 'idle' | 'pending' | 'code_used' | 'enrolled' | 'expired' | 'revoked';

export const RELEASES_URL = 'https://github.com/AprileNunzio/Nuxiva/releases';
const OFFICIAL_PREFIX = `${RELEASES_URL}/download/`;
const KNOWN_ERRORS = new Set(['android_apk_unavailable', 'enroll_https_unavailable', 'enroll_ca_missing', 'enroll_too_many_tokens']);
const QR_OPTIONS = { errorCorrectionLevel: 'M', margin: 2, width: 320 } as const;
const POLL_MS = 3000;
const BASE = '/api/android/enrollment';

export const groupFingerprint = (value: string): string => (value.match(/.{1,4}/g) ?? []).join('-');
export const groupCode = (value: string): string => `${value.slice(0, 3)} ${value.slice(3)}`;

export function useAndroidPairing() {
  const [apk, setApk] = useState<ApkInfo | null>(null);
  const [apkImage, setApkImage] = useState('');
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [pairing, setPairing] = useState<Pairing | null>(null);
  const [image, setImage] = useState('');
  const [phase, setPhase] = useState<PairingPhase>('idle');
  const [remaining, setRemaining] = useState(0);
  const current = useRef<Pairing | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    requestJson<ApkInfo>('/api/android/installer-info', { signal: controller.signal })
      .then(async (result) => {
        if (!result.url.startsWith(OFFICIAL_PREFIX)) return;
        const qr = await QRCode.toDataURL(result.url, QR_OPTIONS);
        if (!controller.signal.aborted) {
          setApk(result);
          setApkImage(qr);
        }
      })
      .catch((cause) => {
        if (!controller.signal.aborted && !(cause instanceof NodeModuleError)) reportError('nodes_android_info_failed', cause);
      })
      .finally(() => !controller.signal.aborted && setLoaded(true));
    return () => controller.abort();
  }, []);

  const clear = useCallback((next: PairingPhase) => {
    current.current = null;
    setPairing(null);
    setImage('');
    setPhase(next);
  }, []);

  useEffect(() => {
    if (!pairing) return undefined;
    const tick = () => {
      const left = Math.max(0, pairing.expires - Math.floor(Date.now() / 1000));
      setRemaining(left);
      if (left === 0) clear('expired');
    };
    tick();
    const timer = window.setInterval(tick, 1000);
    return () => window.clearInterval(timer);
  }, [pairing, clear]);

  useEffect(() => {
    if (!pairing) return undefined;
    const controller = new AbortController();
    const poll = () => {
      requestJson<{ state: string }>(`${BASE}/${encodeURIComponent(pairing.id)}`, { signal: controller.signal })
        .then(({ state }) => {
          if (controller.signal.aborted) return;
          if (state === 'enrolled') clear('enrolled');
          else if (state === 'gone') clear('expired');
          else if (state === 'code_used') setPhase('code_used');
        })
        .catch(() => undefined);
    };
    const timer = window.setInterval(() => !document.hidden && poll(), POLL_MS);
    return () => {
      controller.abort();
      window.clearInterval(timer);
    };
  }, [pairing, clear]);

  const revoke = useCallback(async (quiet = false) => {
    const active = current.current;
    if (!active) return;
    try {
      await requestJson(`${BASE}/${encodeURIComponent(active.id)}`, { method: 'DELETE' });
    } catch (cause) {
      if (!(cause instanceof NodeModuleError && cause.status === 404)) reportError('nodes_android_revoke_failed', cause);
    }
    if (!quiet) clear('revoked');
  }, [clear]);

  const generate = useCallback(async () => {
    setBusy(true);
    setError('');
    try {
      await revoke(true);
      const result = await requestJson<Pairing>(BASE, { method: 'POST', body: '{}' });
      const qr = await QRCode.toDataURL(result.link, QR_OPTIONS);
      current.current = result;
      setImage(qr);
      setPairing(result);
      setPhase('pending');
    } catch (cause) {
      const code = cause instanceof NodeModuleError && KNOWN_ERRORS.has(cause.code) ? cause.code : 'generic';
      setError(code);
      if (code === 'generic') reportError('nodes_android_enrollment_failed', cause);
    } finally {
      setBusy(false);
    }
  }, [revoke]);

  return { apk, apkImage, loaded, busy, error, pairing, image, phase, remaining, generate, revoke: () => void revoke() };
}
