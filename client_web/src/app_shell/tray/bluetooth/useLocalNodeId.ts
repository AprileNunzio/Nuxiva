import { useEffect, useState } from 'react';
import { reportError } from '../../../shared/errors/errorBus';
import { fetchNodes } from '../../../core_apps/nodes/api';

const NODE_ID = /^[A-Za-z0-9_.:-]{1,128}$/;

export function useLocalNodeId(): string | null {
  const [nodeId, setNodeId] = useState<string | null>(null);
  useEffect(() => {
    let disposed = false;
    fetchNodes()
      .then((nodes) => {
        const local = Array.isArray(nodes) ? nodes.find((node) => node.source === 'local') : undefined;
        if (!disposed && local && NODE_ID.test(local.id)) setNodeId(local.id);
      })
      .catch((cause: unknown) => {
        if (!disposed) reportError('node_bluetooth_unavailable', cause);
      });
    return () => {
      disposed = true;
    };
  }, []);
  return nodeId;
}
