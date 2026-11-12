const LOOPBACK = new Set(['localhost', '127.0.0.1', '[::1]', '::1']);

export const CA_PATH = '/nuxiva-ca.crt';

export function secureContextReady(): boolean {
  return typeof window !== 'undefined' && window.isSecureContext === true;
}

export function secureAdminUrl(location: Location = window.location): string | null {
  if (location.protocol === 'https:' || LOOPBACK.has(location.hostname)) {
    return null;
  }
  const mounted = location.pathname === '/admin' || location.pathname.startsWith('/admin/');
  const path = mounted ? location.pathname : `/admin${location.pathname}`;
  return `https://${location.hostname}${path}${location.search}`;
}

export function caDownloadUrl(location: Location = window.location): string {
  return `${location.protocol}//${location.hostname}${CA_PATH}`;
}
