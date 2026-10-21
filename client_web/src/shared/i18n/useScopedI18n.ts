/// <reference types="vite/client" />
import { reportError } from '../errors/errorBus';
import { useState, useEffect, useMemo, useCallback } from 'react';
import { useI18n } from './I18nContext';
import { useAssistantIdentity } from '../identity/IdentityContext';
import { dictionaryText } from './dictionaryText';

const colocatedModules = (import.meta as any).glob(
  '/src/**/language/*.json',
  { eager: true }
);

const dictionaryCache: Record<string, Record<string, Record<string, string>>> = Object.create(null);

function registerScopeDict(scopeKey: string, lang: string, dict: Record<string, string>) {
  if (!scopeKey) return;
  if (!dictionaryCache[scopeKey]) {
    dictionaryCache[scopeKey] = Object.create(null);
  }
  dictionaryCache[scopeKey][lang] = dict;
}

const exactScopes = new Set<string>();

// Pass 1: Register exact scopes directly from their own colocated files
for (const [path, mod] of Object.entries(colocatedModules as Record<string, any>)) {
  const match = path.match(/\/src\/(.+)\/language\/([a-zA-Z0-9_-]+)\.json$/);
  if (match) {
    const rawScope = match[1];
    exactScopes.add(rawScope);
    const lang = match[2].toLowerCase();
    const data = ((mod as any) && (mod as any).default) ? (mod as any).default : mod;
    const dict = (data && data.dictionary) ? data.dictionary : data;
    registerScopeDict(rawScope, lang, dict);
  }
}

// Pass 2: Register fallback aliases only if the target scope is not an exact scope of another module
for (const [path, mod] of Object.entries(colocatedModules as Record<string, any>)) {
  const match = path.match(/\/src\/(.+)\/language\/([a-zA-Z0-9_-]+)\.json$/);
  if (match) {
    const rawScope = match[1];
    const lang = match[2].toLowerCase();
    const data = ((mod as any) && (mod as any).default) ? (mod as any).default : mod;
    const dict = (data && data.dictionary) ? data.dictionary : data;

    const baseScope = rawScope.split('/').pop();
    if (baseScope) {
      if (!exactScopes.has(baseScope) && !dictionaryCache[baseScope]?.[lang]) {
        registerScopeDict(baseScope, lang, dict);
      }
      for (const prefix of ['apps', 'core_apps', 'features', 'node_apps']) {
        const alias = `${prefix}/${baseScope}`;
        if (!exactScopes.has(alias) && !dictionaryCache[alias]?.[lang]) {
          registerScopeDict(alias, lang, dict);
        }
      }
    }
  }
}

function findScopeData(scope: string): Record<string, Record<string, string>> | undefined {
  if (dictionaryCache[scope]) return dictionaryCache[scope];
  const base = scope.split('/').pop();
  if (base) {
    if (dictionaryCache[base]) return dictionaryCache[base];
    if (dictionaryCache[`apps/${base}`]) return dictionaryCache[`apps/${base}`];
    if (dictionaryCache[`core_apps/${base}`]) return dictionaryCache[`core_apps/${base}`];
    if (dictionaryCache[`features/${base}`]) return dictionaryCache[`features/${base}`];
  }
  return undefined;
}

export function useScopedI18n(scope: string) {
  const { lang, setLang } = useI18n();
  const [remoteDict, setRemoteDict] = useState<Record<string, string> | null>(null);

  useEffect(() => {
    setRemoteDict(null);
    const scopeData = findScopeData(scope);
    if (!scopeData || !scopeData[lang]) {
      let isMounted = true;
      const fid = scope.split('/').pop() || scope;
      const fetchLang = async () => {
        try {
          const res = await fetch(`/features/${fid}/language/${lang}.json`);
          if (res.ok) {
            const data = await res.json();
            if (isMounted && data) {
              const dict = data.dictionary || data;
              registerScopeDict(scope, lang, dict);
              registerScopeDict(fid, lang, dict);
              setRemoteDict(dict);
            }
          }
        } catch (cause: unknown) {
          reportError('i18n_remote_unavailable', cause);
        }
      };
      void fetchLang();

      return () => {
        isMounted = false;
      };
    }
  }, [scope, lang]);

  const activeDictionary = useMemo<Record<string, string>>(() => {
    const scopeData = findScopeData(scope) || {};
    if (remoteDict) {
      return remoteDict;
    }
    if (scopeData[lang]) {
      return scopeData[lang];
    }
    if (scopeData['en']) {
      return scopeData['en'];
    }
    if (scopeData['it']) {
      return scopeData['it'];
    }
    const firstAvailable = Object.values(scopeData)[0];
    return firstAvailable || {};
  }, [scope, lang, remoteDict]);

  const fallbackDictionary = useMemo<Record<string, string>>(() => {
    const scopeData = findScopeData(scope) || {};
    return scopeData['en'] || scopeData['it'] || {};
  }, [scope]);

  const { name: assistant } = useAssistantIdentity();

  const t = useCallback(
    (key: string, params?: Record<string, string | number>): string => {
      const prefix = (scope.split('/').pop() || scope) + '.';
      const localKey = key.startsWith(prefix) ? key.slice(prefix.length) : key;
      let text = dictionaryText(activeDictionary, key) ?? dictionaryText(activeDictionary, localKey) ?? dictionaryText(fallbackDictionary, key) ?? dictionaryText(fallbackDictionary, localKey) ?? key;
      const merged: Record<string, string | number> = { assistant, ...params };
      Object.entries(merged).forEach(([k, v]) => {
        text = text.split(`{${k}}`).join(String(v));
      });
      return text;
    },
    [activeDictionary, fallbackDictionary, assistant, scope]
  );

  return { t, lang, setLang };
}

export function getScopedString(scope: string, lang: string, key: string, fallback?: string): string {
  const scopeData = findScopeData(scope);
  if (scopeData) {
    const prefix = (scope.split('/').pop() || scope) + '.';
    const localKey = key.startsWith(prefix) ? key.slice(prefix.length) : key;
    for (const locale of [...new Set([lang, 'en', 'it', ...Object.keys(scopeData)])]) {
      const text = dictionaryText(scopeData[locale], key) ?? dictionaryText(scopeData[locale], localKey);
      if (text !== undefined) return text;
    }
  }
  return fallback || key;
}
