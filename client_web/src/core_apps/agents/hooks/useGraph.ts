import { useEffect, useState } from 'react';
import { GraphSnapshot, fetchGraph } from '../data/graphApi';

const POLL_MS = 15000;

export function useGraph(): GraphSnapshot | null {
  const [snapshot, setSnapshot] = useState<GraphSnapshot | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    fetchGraph(controller.signal)
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
