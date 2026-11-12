import { useEffect, useState } from 'react';
import { reportError } from '../../../shared/errors/errorBus';
import { ControlScope } from '../../console/data/nodeConsoleApi';
import { PairedNode, fetchPairedNode } from '../data/pairedNodeApi';

export function usePairedNode(nodeId: string, scope: ControlScope): { readonly node: PairedNode | null; readonly loading: boolean } {
  const [node, setNode] = useState<PairedNode | null>(null);
  const [loading, setLoading] = useState(scope === 'paired');

  useEffect(() => {
    if (scope !== 'paired') {
      setNode(null);
      setLoading(false);
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    fetchPairedNode(nodeId, controller.signal)
      .then(setNode)
      .catch((cause: unknown) => {
        if (!controller.signal.aborted) {
          reportError('node_inventory_unavailable', cause);
        }
      })
      .finally(() => !controller.signal.aborted && setLoading(false));
    return () => controller.abort();
  }, [nodeId, scope]);

  return { node, loading };
}
