import { useEffect, useState } from 'react';
import { reportError } from '../../../shared/errors/errorBus';
import { NodeControl, fetchNodeControl } from '../data/nodeConsoleApi';

export function useNodeControl(nodeId: string): NodeControl | null {
  const [control, setControl] = useState<NodeControl | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setControl(null);
    fetchNodeControl(nodeId, controller.signal)
      .then(setControl)
      .catch((cause: unknown) => {
        if (!controller.signal.aborted) {
          reportError('node_control_unavailable', cause);
          setControl({ scope: 'mesh', commands: [] });
        }
      });
    return () => controller.abort();
  }, [nodeId]);

  return control;
}
