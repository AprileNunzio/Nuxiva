import { useCallback, useEffect, useState } from 'react';
import { reportError } from '../../shared/errors/errorBus';

type LegacyDocument = Document & { webkitFullscreenElement?: Element | null; webkitFullscreenEnabled?: boolean; webkitExitFullscreen?: () => Promise<void> | void };
type LegacyElement = HTMLElement & { webkitRequestFullscreen?: () => Promise<void> | void };

const doc = () => document as LegacyDocument;
const activeElement = () => doc().fullscreenElement ?? doc().webkitFullscreenElement ?? null;
const supported = () => typeof document !== 'undefined' && Boolean(doc().fullscreenEnabled || doc().webkitFullscreenEnabled);

export function useFullscreen() {
  const [available] = useState(supported);
  const [active, setActive] = useState(() => typeof document !== 'undefined' && activeElement() !== null);

  useEffect(() => {
    if (!available) return;
    const sync = () => setActive(activeElement() !== null);
    document.addEventListener('fullscreenchange', sync);
    document.addEventListener('webkitfullscreenchange', sync);
    return () => {
      document.removeEventListener('fullscreenchange', sync);
      document.removeEventListener('webkitfullscreenchange', sync);
    };
  }, [available]);

  const toggle = useCallback(async () => {
    if (!available) return;
    const root = document.documentElement as LegacyElement;
    try {
      if (activeElement()) {
        await (document.exitFullscreen ? document.exitFullscreen() : doc().webkitExitFullscreen?.());
      } else if (root.requestFullscreen) {
        await root.requestFullscreen({ navigationUI: 'hide' });
      } else {
        await root.webkitRequestFullscreen?.();
      }
    } catch (error) {
      reportError('fullscreen_toggle_failed', error);
    }
  }, [available]);

  return { available, active, toggle };
}
