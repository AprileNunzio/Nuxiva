import { useCallback, useEffect, useRef, useState } from 'react';
import { reportError } from '../../../shared/errors/errorBus';
import { AudioChange, AudioSide, LocalAudioState, fetchLocalAudio, updateLocalAudio } from '../data/localAudioApi';

const REFRESH_MS = 8000;
const VOLUME_DEBOUNCE_MS = 250;

export interface LocalAudioController {
  readonly state: LocalAudioState | null;
  readonly busy: boolean;
  readonly apply: (side: AudioSide, change: AudioChange) => void;
}

export function useLocalAudio(enabled: boolean): LocalAudioController {
  const [state, setState] = useState<LocalAudioState | null>(null);
  const [busy, setBusy] = useState(false);
  const pending = useRef<number | null>(null);

  useEffect(() => {
    if (!enabled) {
      return;
    }
    let controller = new AbortController();
    const load = () => {
      controller.abort();
      controller = new AbortController();
      fetchLocalAudio(controller.signal)
        .then(setState)
        .catch((cause: unknown) => {
          if (!controller.signal.aborted) {
            reportError('node_audio_unavailable', cause);
          }
        });
    };
    load();
    const timer = window.setInterval(load, REFRESH_MS);
    return () => {
      controller.abort();
      window.clearInterval(timer);
    };
  }, [enabled]);

  const send = useCallback(async (side: AudioSide, change: AudioChange) => {
    setBusy(true);
    try {
      setState(await updateLocalAudio(side, change));
    } catch (cause) {
      reportError('node_audio_update_failed', cause);
    } finally {
      setBusy(false);
    }
  }, []);

  const apply = useCallback(
    (side: AudioSide, change: AudioChange) => {
      setState((current) => (current ? { ...current, [side]: { ...current[side], ...change } } : current));
      if (pending.current !== null) {
        window.clearTimeout(pending.current);
      }
      if (change.volume !== undefined && change.device === undefined) {
        pending.current = window.setTimeout(() => void send(side, change), VOLUME_DEBOUNCE_MS);
        return;
      }
      void send(side, change);
    },
    [send],
  );

  return { state, busy, apply };
}
