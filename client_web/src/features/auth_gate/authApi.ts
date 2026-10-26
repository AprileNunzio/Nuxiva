export type LoginFailure = 'invalid_credentials' | 'rate_limited' | 'rejected' | 'unreachable';

export class LoginError extends Error {
  constructor(readonly reason: LoginFailure) {
    super(reason);
    this.name = 'LoginError';
  }
}

const JSON_HEADERS = { Accept: 'application/json', 'Content-Type': 'application/json' };
const USERNAME_PATTERN = /^[a-z_][a-z0-9_.-]{0,31}$/i;

export function isValidUsername(username: string): boolean {
  return USERNAME_PATTERN.test(username);
}

export async function fetchSessionUser(): Promise<string | null> {
  const response = await fetch('/api/auth/me', { headers: { Accept: 'application/json' }, cache: 'no-store' });
  if (response.status === 401) {
    return null;
  }
  if (!response.ok) {
    throw new LoginError('unreachable');
  }
  const payload: unknown = await response.json();
  const user = typeof payload === 'object' && payload !== null ? (payload as { user?: unknown }).user : null;
  return typeof user === 'string' && isValidUsername(user) ? user : null;
}

export async function login(username: string, password: string): Promise<string> {
  if (!isValidUsername(username) || password.length === 0 || password.length > 1024) {
    throw new LoginError('invalid_credentials');
  }
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify({ username, password }),
    cache: 'no-store',
  });
  if (response.status === 401) {
    throw new LoginError('invalid_credentials');
  }
  if (response.status === 429) {
    throw new LoginError('rate_limited');
  }
  if (!response.ok) {
    throw new LoginError('rejected');
  }
  return username;
}

export async function logout(): Promise<void> {
  const response = await fetch('/api/auth/logout', { method: 'POST', headers: JSON_HEADERS, cache: 'no-store' });
  if (!response.ok) {
    throw new LoginError('rejected');
  }
}
