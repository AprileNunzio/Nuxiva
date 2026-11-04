import { useEffect, useState } from 'react';
import { reportError } from '../../shared/errors/errorBus';
import { parseHardwareCapabilities, type HardwareCapabilities } from './capabilities';

export function useHardwareCapabilities() {
  const [capabilities, setCapabilities] = useState<HardwareCapabilities | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    const refresh = async () => {
      try {
        const response = await fetch('/api/hardware/capabilities', {
          credentials: 'same-origin', signal: controller.signal,
        });
        if (!response.ok) throw new Error(`hardware_http_${response.status}`);
        const parsed = parseHardwareCapabilities(await response.json());
        if (!controller.signal.aborted) setCapabilities(parsed);
      } catch (cause) {
        if (!controller.signal.aborted) {
          setCapabilities(null);
          reportError('hardware_capabilities_unavailable', cause);
        }
      } finally {
        if (!controller.signal.aborted) timer = setTimeout(refresh, 4000);
      }
    };
    void refresh();
    return () => {
      controller.abort();
      if (timer !== undefined) clearTimeout(timer);
    };
  }, []);

  return (name: string): boolean | undefined => capabilities === null ? undefined : Boolean(capabilities[name]?.length);
}
