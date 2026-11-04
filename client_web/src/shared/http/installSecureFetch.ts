import { emitSessionExpired } from './sessionEvents';
import { adminPath } from './basePath';

export const CSRF_HEADER = 'X-Nuxiva-Request';
const AUTH_PREFIX = '/api/auth/';
const MCP_PREFIX = '/mcp';
let installed = false;

function resolveUrl(input: RequestInfo | URL): URL {
  if (input instanceof URL) {
    return input;
  }
  return new URL(typeof input === 'string' ? input : input.url, window.location.href);
}

export function installSecureFetch(): void {
  if (installed) {
    return;
  }
  installed = true;
  const nativeFetch = window.fetch.bind(window);

  window.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const url = resolveUrl(input);
    if (url.origin !== window.location.origin) {
      return nativeFetch(input, init);
    }
    const headers = new Headers(init?.headers ?? (input instanceof Request ? input.headers : undefined));
    headers.set(CSRF_HEADER, '1');
    const target = adminPath(url.pathname);
    const request = target === url.pathname ? input : input instanceof Request
      ? new Request(`${url.origin}${target}${url.search}`, input)
      : `${url.origin}${target}${url.search}`;
    const response = await nativeFetch(request, { ...init, headers, credentials: 'include' });
    if (response.status === 401 && !url.pathname.startsWith(AUTH_PREFIX) && !url.pathname.startsWith(MCP_PREFIX)) {
      emitSessionExpired();
    }
    return response;
  };
}
