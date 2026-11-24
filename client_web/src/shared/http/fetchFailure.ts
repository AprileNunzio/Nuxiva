export class FetchFailure extends TypeError {
  constructor(
    readonly method: string,
    readonly path: string,
    readonly online: boolean,
    readonly elapsedMs: number,
    readonly reason: string,
  ) {
    super(reason || 'fetch_failed');
    this.name = 'FetchFailure';
  }
}

export function requestMethod(input: RequestInfo | URL, init?: RequestInit): string {
  const method = init?.method ?? (typeof Request !== 'undefined' && input instanceof Request ? input.method : 'GET');
  return method.toUpperCase().slice(0, 10);
}

export function displayPath(url: URL, sameOrigin: boolean): string {
  const path = url.pathname.slice(0, 200);
  return sameOrigin ? path : `${url.origin}${path}`;
}

const isAbort = (cause: unknown): boolean =>
  typeof cause === 'object' && cause !== null && ['AbortError', 'TimeoutError'].includes((cause as { name?: unknown }).name as string);

export async function guardFetch(call: () => Promise<Response>, method: string, path: string): Promise<Response> {
  const started = Date.now();
  try {
    return await call();
  } catch (cause) {
    if (!isAbort(cause) && cause instanceof TypeError) {
      throw new FetchFailure(method, path, typeof navigator === 'undefined' || navigator.onLine !== false, Date.now() - started, cause.message);
    }
    throw cause;
  }
}
