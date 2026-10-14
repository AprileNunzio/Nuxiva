import { useState, useEffect, useCallback } from 'react';
import {
  CognitiveEngineId,
  CognitiveEngineProfile,
  EngineVersionStatusResponse,
  EngineTelemetryUpdate,
} from './types';

export const useCognitiveEngine = () => {
  const [configuredVersion, setConfiguredVersion] = useState<CognitiveEngineId>('nuxiva-6.5-auto');
  const [activeRuntime, setActiveRuntime] = useState<CognitiveEngineId>('nuxiva-5.0-veloce');
  const [latencyMs, setLatencyMs] = useState<number>(25);
  const [vramMb, setVramMb] = useState<number>(1200);
  const [engines, setEngines] = useState<CognitiveEngineProfile[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch('/api/v2/brain/engine-version', {
        headers: { Accept: 'application/json' },
      });
      if (!res.ok) {
        throw new Error(`HTTP_${res.status}`);
      }
      const data: EngineVersionStatusResponse = await res.json();
      setConfiguredVersion(data.current_configured);
      setActiveRuntime(data.active_runtime);
      setLatencyMs(data.latency_sla_ms);
      setVramMb(data.vram_mb);
      setEngines(data.engines);
      setErrorMessage(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'FETCH_ERROR';
      setErrorMessage(msg);
    }
  }, []);

  const switchEngine = useCallback(async (version: CognitiveEngineId) => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const res = await fetch('/api/v2/brain/engine-version', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify({ version }),
      });
      if (!res.ok) {
        throw new Error(`HTTP_${res.status}`);
      }
      const data: EngineVersionStatusResponse = await res.json();
      setConfiguredVersion(data.current_configured);
      setActiveRuntime(data.active_runtime);
      setLatencyMs(data.latency_sla_ms);
      setVramMb(data.vram_mb);
      setEngines(data.engines);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'SWITCH_ERROR';
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/v2/brain/engine-version/ws`;
    let ws: WebSocket | null = null;
    try {
      ws = new WebSocket(wsUrl);
      ws.onmessage = (event) => {
        try {
          const telemetry: EngineTelemetryUpdate = JSON.parse(event.data);
          setActiveRuntime(telemetry.version);
          setLatencyMs(telemetry.synaptic_latency_ms);
          setVramMb(telemetry.vram_allocated_mb);
        } catch {}
      };
    } catch {}

    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, [fetchStatus]);

  return {
    configuredVersion,
    activeRuntime,
    latencyMs,
    vramMb,
    engines,
    isLoading,
    errorMessage,
    switchEngine,
    refetch: fetchStatus,
  };
};
