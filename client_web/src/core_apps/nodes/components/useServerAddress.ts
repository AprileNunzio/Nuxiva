import { useEffect, useState } from 'react';
import { requestJson } from '../../../node_apps/shared/data/http';

export const useServerAddress = (): string => {
  const [address, setAddress] = useState(() => window.location.origin);

  useEffect(() => {
    const controller = new AbortController();
    requestJson<{ server: string }>('/api/nodes/connection', { signal: controller.signal })
      .then((result) => {
        if (typeof result.server === 'string' && /^https?:\/\/[^\s]+$/i.test(result.server)) {
          setAddress(result.server);
        }
      })
      .catch(() => setAddress(window.location.origin));
    return () => controller.abort();
  }, []);

  return address;
};
