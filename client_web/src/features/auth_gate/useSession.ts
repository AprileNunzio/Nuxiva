import { useCallback, useEffect, useState } from 'react';
import { reportError } from '../../shared/errors/errorBus';
import { onSessionExpired } from '../../shared/http/sessionEvents';
import { fetchSessionUser, logout as apiLogout } from './authApi';

export type SessionState =
  | { readonly status: 'checking' }
  | { readonly status: 'anonymous'; readonly expired: boolean }
  | { readonly status: 'authenticated'; readonly user: string };

export interface SessionController {
  readonly session: SessionState;
  readonly signedIn: (user: string) => void;
  readonly signOut: () => Promise<void>;
}

export function useSession(): SessionController {
  const [session, setSession] = useState<SessionState>({ status: 'checking' });

  useEffect(() => {
    let active = true;
    fetchSessionUser()
      .then((user) => {
        if (active) {
          setSession(user ? { status: 'authenticated', user } : { status: 'anonymous', expired: false });
        }
      })
      .catch((cause: unknown) => {
        reportError('session_check_failed', cause);
        if (active) {
          setSession({ status: 'anonymous', expired: false });
        }
      });
    const unsubscribe = onSessionExpired(() => setSession({ status: 'anonymous', expired: true }));
    return () => {
      active = false;
      unsubscribe();
    };
  }, []);

  const signedIn = useCallback((user: string) => setSession({ status: 'authenticated', user }), []);

  const signOut = useCallback(async () => {
    await apiLogout();
    setSession({ status: 'anonymous', expired: false });
  }, []);

  return { session, signedIn, signOut };
}
