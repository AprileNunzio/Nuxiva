import { useEffect, useState } from 'react';
import { Observability, fetchObservability } from '../data/observabilityApi';

const POLL_MS = 8000;

export function useObservability(): Observability | null {
  const [snapshot, setSnapshot] = useState<Observability | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    fetchObservability(controller.signal)
      .then(setSnapshot)
      .catch(() => undefined);
    const timer = window.setTimeout(() => setTick((value) => value + 1), document.hidden ? POLL_MS * 4 : POLL_MS);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [tick]);

  return snapshot;
}
