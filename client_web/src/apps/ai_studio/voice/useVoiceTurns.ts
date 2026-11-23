import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchVoiceTurns } from './api';
import type { VoiceChannelFilter, VoiceStats, VoiceTurn } from './types';

const POLL_MS = 4000;
const PAGE = 40;

function merge(fresh: VoiceTurn[], current: VoiceTurn[]): VoiceTurn[] {
  const seen = new Set(fresh.map((turn) => turn.id));
  return [...fresh, ...current.filter((turn) => !seen.has(turn.id))].sort((a, b) => b.at - a.at);
}

export function useVoiceTurns(channel: VoiceChannelFilter, query: string, live: boolean) {
  const [turns, setTurns] = useState<VoiceTurn[]>([]);
  const [stats, setStats] = useState<VoiceStats>({});
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [hasMore, setHasMore] = useState(false);
  const controller = useRef<AbortController | null>(null);

  const refresh = useCallback(async (reset: boolean) => {
    controller.current?.abort();
    const ctrl = new AbortController();
    controller.current = ctrl;
    try {
      const page = await fetchVoiceTurns({ channel, q: query, limit: PAGE }, ctrl.signal);
      setTurns((prev) => (reset ? page.items : merge(page.items, prev)));
      setStats(page.stats);
      if (reset) setHasMore(page.items.length >= PAGE);
      setError(null);
    } catch (err) {
      if (ctrl.signal.aborted) return;
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      if (!ctrl.signal.aborted) setLoading(false);
    }
  }, [channel, query]);

  useEffect(() => {
    setLoading(true);
    void refresh(true);
    return () => controller.current?.abort();
  }, [refresh]);

  useEffect(() => {
    if (!live) return undefined;
    const tick = () => {
      if (document.visibilityState === 'visible') void refresh(false);
    };
    const timer = window.setInterval(tick, POLL_MS);
    return () => window.clearInterval(timer);
  }, [live, refresh]);

  const loadMore = useCallback(async () => {
    const oldest = turns[turns.length - 1];
    if (!oldest) return;
    try {
      const page = await fetchVoiceTurns({ channel, q: query, limit: PAGE, before: oldest.at });
      setTurns((prev) => merge(prev, page.items));
      setHasMore(page.items.length >= PAGE);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, [channel, query, turns]);

  const patch = useCallback((id: string, change: (turn: VoiceTurn) => VoiceTurn | null) => {
    setTurns((prev) => prev.flatMap((turn) => {
      if (turn.id !== id) return [turn];
      const next = change(turn);
      return next ? [next] : [];
    }));
  }, []);

  return { turns, stats, error, loading, hasMore, refresh: () => refresh(true), loadMore, patch };
}
