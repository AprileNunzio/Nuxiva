/** Only the latest request may publish a result or an error. */
export function latestRequest<T>(load: (signal: AbortSignal) => Promise<T>, accept: (value: T) => void, reject: (cause: unknown) => void) {
  let current: AbortController | undefined;
  let disposed = false;
  return {
    run() {
      if (disposed) return;
      current?.abort();
      const request = new AbortController();
      current = request;
      void load(request.signal).then(value => {
        if (!request.signal.aborted) accept(value);
      }).catch(cause => {
        if (!request.signal.aborted) reject(cause);
      });
    },
    dispose() { disposed = true; current?.abort(); },
  };
}
