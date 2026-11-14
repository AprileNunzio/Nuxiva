import { useCallback, useState } from 'react';
import { NodeModuleError } from '../../node_apps/shared/data/http';

export type Notice = { readonly kind: 'ok' | 'error'; readonly key: string } | null;

export function errorKey(cause: unknown): string {
  if (cause instanceof NodeModuleError) {
    if (cause.status === 409) return 'error_blocked';
    if (cause.status === 503) return 'unreachable';
    if (cause.status === 400) return 'error_invalid';
  }
  return 'error_generic';
}

export function useAction(onDone: () => void) {
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);
  const run = useCallback(
    async (task: () => Promise<unknown>, okKey: string): Promise<boolean> => {
      setBusy(true);
      try {
        await task();
        setNotice({ kind: 'ok', key: okKey });
        onDone();
        return true;
      } catch (cause) {
        setNotice({ kind: 'error', key: errorKey(cause) });
        return false;
      } finally {
        setBusy(false);
      }
    },
    [onDone],
  );
  return { busy, notice, run, clear: () => setNotice(null) };
}
