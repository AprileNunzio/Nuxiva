import { useCallback, useEffect, useState } from 'react';
import { reportError } from '../../shared/errors/errorBus';
import { CognitiveEngineId, CognitiveEngineProfile, EngineVersionStatusResponse } from './types';

const ENDPOINT = '/api/v2/brain/engine-version';

async function request(init?: RequestInit): Promise<EngineVersionStatusResponse> {
  const res = await fetch(ENDPOINT, { cache: 'no-store', ...init, headers: { Accept: 'application/json', 'Content-Type': 'application/json', ...init?.headers } });
  if (!res.ok) {
    throw new Error(`HTTP_${res.status}`);
  }
  return (await res.json()) as EngineVersionStatusResponse;
}

export const useCognitiveEngine = () => {
  const [configuredVersion, setConfiguredVersion] = useState<CognitiveEngineId | null>(null);
  const [engines, setEngines] = useState<CognitiveEngineProfile[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const apply = (data: EngineVersionStatusResponse) => {
    setConfiguredVersion(data.current_configured);
    setEngines(data.engines);
  };

  const fetchStatus = useCallback(async () => {
    try {
      apply(await request());
    } catch (cause) {
      reportError('engine_status_failed', cause);
    }
  }, []);

  const switchEngine = useCallback(async (version: CognitiveEngineId) => {
    setIsLoading(true);
    try {
      apply(await request({ method: 'POST', body: JSON.stringify({ version }) }));
    } catch (cause) {
      reportError('engine_switch_failed', cause);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchStatus();
  }, [fetchStatus]);

  return { configuredVersion, engines, isLoading, switchEngine, refetch: fetchStatus };
};
