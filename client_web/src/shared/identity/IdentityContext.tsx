import React, { createContext, useContext, useEffect, useState } from 'react';
import { reportError } from '../errors/errorBus';

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
    let controller = new AbortController();
    const load = () => {
      controller.abort();
      controller = new AbortController();
      fetch('/api/system/identity', { headers: { Accept: 'application/json' }, cache: 'no-store', signal: controller.signal })
        .then((response) => {
          if (!response.ok) {
            throw new Error(`identity_http_${response.status}`);
          }
          return response.json();
        })
        .then((payload: unknown) => setIdentity(parseIdentity(payload)))
        .catch((cause: unknown) => {
          if (!controller.signal.aborted) {
            reportError('identity_unavailable', cause);
          }
        });
    };
    load();
    window.addEventListener('focus', load);
    return () => {
      controller.abort();
      window.removeEventListener('focus', load);
    };
  }, []);

  return <IdentityContext.Provider value={identity}>{children}</IdentityContext.Provider>;
};

export function useAssistantIdentity(): AssistantIdentity {
  return useContext(IdentityContext);
}
