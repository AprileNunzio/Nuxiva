import { useCallback, useEffect, useRef, useState } from 'react';
import { NodeModuleError } from '../../shared/data/http';
import { MicTestReport, MicTestRequest, runMicTest } from '../data/micTestApi';

export type MicTestPhase = 'idle' | 'recording' | 'ready' | 'error';

export interface MicTestController {
  readonly phase: MicTestPhase;
  readonly remaining: number;
  readonly report: MicTestReport | null;
  readonly rawUrl: string | null;
  readonly processedUrl: string | null;
  readonly error: string | null;
  readonly record: (request: MicTestRequest) => Promise<void>;
}

const KNOWN_ERRORS = new Set(['mic_busy', 'mic_unavailable', 'mic_stalled', 'mic_closed']);

function errorCode(cause: unknown): string {
  if (cause instanceof NodeModuleError) {
    if (KNOWN_ERRORS.has(cause.code)) {
      return cause.code;
    }
    return cause.status === 401 || cause.status === 403 ? 'mictest_denied' : 'mictest_failed';
  }
  return 'mictest_failed';
}

export function useMicTest(): MicTestController {
  const [phase, setPhase] = useState<MicTestPhase>('idle');
  const [remaining, setRemaining] = useState(0);
  const [report, setReport] = useState<MicTestReport | null>(null);
  const [urls, setUrls] = useState<{ raw: string; processed: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const controller = useRef<AbortController | null>(null);
  const timer = useRef<number | null>(null);

  const clearTimer = () => {
    if (timer.current !== null) {
      window.clearInterval(timer.current);
      timer.current = null;
    }
  };

  useEffect(() => {
    return () => {
      if (urls) {
        URL.revokeObjectURL(urls.raw);
        URL.revokeObjectURL(urls.processed);
      }
    };
  }, [urls]);

  useEffect(
    () => () => {
      controller.current?.abort();
      clearTimer();
    },
    [],
  );

  const record = useCallback(async (request: MicTestRequest) => {
    controller.current?.abort();
    const current = new AbortController();
    controller.current = current;
    setError(null);
    setPhase('recording');
    const endsAt = Date.now() + request.seconds * 1000;
    setRemaining(request.seconds);
    clearTimer();
    timer.current = window.setInterval(() => setRemaining(Math.max(0, Math.ceil((endsAt - Date.now()) / 1000))), 200);
    try {
      const result = await runMicTest(request, current.signal);
      if (current.signal.aborted) {
        return;
      }
      setReport(result.report);
      setUrls({ raw: URL.createObjectURL(result.raw), processed: URL.createObjectURL(result.processed) });
      setPhase('ready');
    } catch (cause) {
      if (current.signal.aborted) {
        return;
      }
      console.error('[nuxiva:mictest]', cause);
      setError(errorCode(cause));
      setPhase('error');
    } finally {
      clearTimer();
      setRemaining(0);
    }
  }, []);

  return { phase, remaining, report, rawUrl: urls?.raw ?? null, processedUrl: urls?.processed ?? null, error, record };
}
