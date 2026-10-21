import { useCallback, useEffect, useState } from 'react';
import { reportError } from '../../../shared/errors/errorBus';
import { fetchTopology } from '../data/meshApi';
import { MeshTelemetryStream } from '../data/meshStream';
import { MeshSnapshot, StreamState } from '../domain/types';

export interface MeshTopologyState {
  readonly snapshot: MeshSnapshot | null;
  readonly streamState: StreamState;
  readonly applyLocalParent: (neuronId: string, parentId: string | null) => void;
}

export function useMeshTopology(): MeshTopologyState {
  const [snapshot, setSnapshot] = useState<MeshSnapshot | null>(null);
  const [streamState, setStreamState] = useState<StreamState>('connecting');

  useEffect(() => {
    const controller = new AbortController();
    fetchTopology(controller.signal)
      .then((initial) => setSnapshot((current) => current ?? initial))
      .catch((cause: unknown) => {
        if (!controller.signal.aborted) {
          reportError('topology_unavailable', cause);
        }
      });
    const stream = new MeshTelemetryStream({
      onSnapshot: setSnapshot,
      onState: setStreamState,
      onError: (code, cause) => reportError(code, cause),
    });
    stream.start();
    return () => {
      controller.abort();
      stream.stop();
    };
  }, []);

  const applyLocalParent = useCallback((neuronId: string, parentId: string | null) => {
    setSnapshot((current) =>
      current
        ? { ...current, neurons: current.neurons.map((n) => (n.id === neuronId ? { ...n, parentId } : n)) }
        : current,
    );
  }, []);

  return { snapshot, streamState, applyLocalParent };
}
