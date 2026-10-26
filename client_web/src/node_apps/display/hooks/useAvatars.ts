import { useCallback, useEffect, useState } from 'react';
import { reportError } from '../../../shared/errors/errorBus';
import { AvatarLibrary, fetchAvatars } from '../data/displayApi';

export interface AvatarsHandle {
  readonly library: AvatarLibrary | null;
  readonly busy: string | null;
  readonly run: (key: string, task: () => Promise<AvatarLibrary>, errorCode: string) => Promise<boolean>;
}

export function useAvatars(enabled: boolean): AvatarsHandle {
  const [library, setLibrary] = useState<AvatarLibrary | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled) {
      return;
    }
    const controller = new AbortController();
    fetchAvatars(controller.signal)
      .then(setLibrary)
      .catch((cause: unknown) => !controller.signal.aborted && reportError('node_avatars_unavailable', cause));
    return () => controller.abort();
  }, [enabled]);

  const run = useCallback(async (key: string, task: () => Promise<AvatarLibrary>, errorCode: string) => {
    setBusy(key);
    try {
      setLibrary(await task());
      return true;
    } catch (cause) {
      reportError(errorCode, cause);
      return false;
    } finally {
      setBusy(null);
    }
  }, []);

  return { library, busy, run };
}
