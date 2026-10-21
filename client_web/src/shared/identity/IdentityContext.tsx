import React, { createContext, useContext, useEffect, useState } from 'react';
import { latestRequest } from '../http/latestRequest';

export const DEFAULT_ASSISTANT_NAME = 'Nuxiva';
const NAME_PATTERN = /^[\p{L}\p{N}][\p{L}\p{N}\s'’.-]{0,31}$/u;

export interface AssistantIdentity {
  readonly name: string;
  readonly wakeWord: string;
  readonly wakePhrases: readonly string[];
}

const FALLBACK: AssistantIdentity = {
  name: DEFAULT_ASSISTANT_NAME,
  wakeWord: DEFAULT_ASSISTANT_NAME.toLowerCase(),
  wakePhrases: [DEFAULT_ASSISTANT_NAME.toLowerCase()],
};

const IdentityContext = createContext<AssistantIdentity>(FALLBACK);

function parseIdentity(payload: unknown): AssistantIdentity {
  if (typeof payload !== 'object' || payload === null) {
    return FALLBACK;
  }
  const record = payload as Record<string, unknown>;
  const name = typeof record.assistant_name === 'string' ? record.assistant_name.trim() : '';
  if (!NAME_PATTERN.test(name)) {
    return FALLBACK;
  }
  const phrases = Array.isArray(record.wake_phrases)
    ? record.wake_phrases.filter((p): p is string => typeof p === 'string' && p.length <= 48).slice(0, 8)
    : [];
  return { name, wakeWord: name.toLowerCase(), wakePhrases: phrases.length > 0 ? phrases : [name.toLowerCase()] };
}

export const IdentityProvider: React.FC<{ readonly children: React.ReactNode }> = ({ children }) => {
  const [identity, setIdentity] = useState<AssistantIdentity>(FALLBACK);

  useEffect(() => {
    const request = latestRequest(signal =>
      fetch('/api/system/identity', { headers: { Accept: 'application/json' }, cache: 'no-store', signal })
        .then((response) => {
          if (!response.ok) {
            throw new Error(`identity_http_${response.status}`);
          }
          return response.json();
        })
        .then((payload: unknown) => parseIdentity(payload)),
      setIdentity,
      (cause) => {
        setIdentity(FALLBACK);
        if (typeof console !== 'undefined' && console.debug) {
          console.debug('[identity] Using fallback assistant identity:', cause);
        }
      });
    const load = () => request.run();
    load();
    window.addEventListener('focus', load);
    window.addEventListener('online', load);
    return () => {
      request.dispose();
      window.removeEventListener('focus', load);
      window.removeEventListener('online', load);
    };
  }, []);

  return <IdentityContext.Provider value={identity}>{children}</IdentityContext.Provider>;
};

export function useAssistantIdentity(): AssistantIdentity {
  return useContext(IdentityContext);
}
