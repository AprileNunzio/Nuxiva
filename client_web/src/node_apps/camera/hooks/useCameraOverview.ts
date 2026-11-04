import { useCallback, useEffect, useState } from 'react';
import { reportError } from '../../../shared/errors/errorBus';
import { CameraOverview, fetchOverview } from '../data/camerasApi';

export function useCameraOverview(enabled: boolean): { readonly overview: CameraOverview | null; readonly refresh: () => void } {
  const [overview, setOverview] = useState<CameraOverview | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!enabled) {
      return;
    }
    const controller = new AbortController();
    fetchOverview(controller.signal)
      .then(setOverview)
      .catch((cause: unknown) => !controller.signal.aborted && reportError('node_cameras_unavailable', cause));
    return () => controller.abort();
  }, [enabled, tick]);

  const refresh = useCallback(() => setTick((value) => value + 1), []);
  return { overview, refresh };
}
