import React, { createContext, useContext } from 'react';
import { Loader2 } from 'lucide-react';
import { LoginView } from './LoginView';
import { useSession } from './useSession';

interface SessionContextValue {
  readonly user: string;
  readonly signOut: () => Promise<void>;
}

const SessionContext = createContext<SessionContextValue | null>(null);

export function useAuthenticatedSession(): SessionContextValue {
  const value = useContext(SessionContext);
  if (!value) {
    throw new Error('useAuthenticatedSession must be used inside AuthGate');
  }
  return value;
}

export const AuthGate: React.FC<{ readonly children: React.ReactNode }> = ({ children }) => {
  const { session, signedIn, signOut } = useSession();

  if (session.status === 'checking') {
    return (
      <div className="flex min-h-[100dvh] items-center justify-center bg-[#02040a]" role="status" aria-busy="true">
        <Loader2 className="h-8 w-8 animate-spin text-cyan-300" aria-hidden="true" />
      </div>
    );
  }

  if (session.status === 'anonymous') {
    return <LoginView expired={session.expired} onSignedIn={signedIn} />;
  }

  return <SessionContext.Provider value={{ user: session.user, signOut }}>{children}</SessionContext.Provider>;
};
