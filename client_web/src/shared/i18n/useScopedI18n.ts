/// <reference types="vite/client" />
import { useState, useEffect, useMemo, useCallback } from 'react';
import { useI18n } from './I18nContext';
import { useAssistantIdentity } from '../identity/IdentityContext';

// Scoperta automatica e dinamica di TUTTI i file di lingua colocated presenti nell'albero src.
// Qualsiasi nuova lingua aggiunta a runtime o in fase di build (it, en, fr, es, de, ja, zh, ecc.)
// viene caricata automaticamente senza mai dover modificare o importare manualmente singoli file nei componenti.
const colocatedModules = (import.meta as any).glob(
  '/src/**/language/*.json',
  { eager: true }
);

// Cache in memoria per i dizionari caricati sia da bundle locale che da API remota
const dictionaryCache: Record<string, Record<string, Record<string, string>>> = {};

// Indicizza i moduli scoperti dinamicamente all'avvio
for (const [path, mod] of Object.entries(colocatedModules as Record<string, any>)) {
  // Esempio path: "/src/mesh_canvas/language/it.json" o "/src/core_apps/habits/language/en.json"
  const match = path.match(/\/src\/(.+)\/language\/([a-zA-Z0-9_-]+)\.json$/);
  if (match) {
    const scope = match[1]; // es: "mesh_canvas", "core_apps/habits", "habits"
    const lang = match[2].toLowerCase(); // es: "it", "en", "fr", "es"
    const data = ((mod as any) && (mod as any).default) ? (mod as any).default : mod;
    const dict = (data && data.dictionary) ? data.dictionary : data;

    if (!dictionaryCache[scope]) {
      dictionaryCache[scope] = {};
    }
    dictionaryCache[scope][lang] = dict;

    // Indicizza anche per basename se lo scope è nidificato (es: "habits" per "core_apps/habits")
    const baseScope = scope.split('/').pop();
    if (baseScope && baseScope !== scope) {
      if (!dictionaryCache[baseScope]) {
        dictionaryCache[baseScope] = {};
      }
      dictionaryCache[baseScope][lang] = dict;
    }
  }
}

export function useScopedI18n(scope: string) {
  const { lang, setLang } = useI18n();
  const [remoteDict, setRemoteDict] = useState<Record<string, string> | null>(null);

  // Se la lingua attiva non è presente nella cache locale (es. nuova lingua installata a runtime sul server),
  // tentiamo il caricamento asincrono via API REST dal resolver colocated backend
  useEffect(() => {
    const scopeData = dictionaryCache[scope];
    if (!scopeData || !scopeData[lang]) {
      let isMounted = true;
      const fid = scope.split('/').pop() || scope;
      fetch(`/api/features/${fid}/language/${lang}.json`)
        .then((res) => {
          if (res.ok) return res.json();
          return null;
        })
        .then((data) => {
          if (isMounted && data) {
            const dict = data.dictionary || data;
            if (!dictionaryCache[scope]) {
              dictionaryCache[scope] = {};
            }
            dictionaryCache[scope][lang] = dict;
            setRemoteDict(dict);
          }
        })
        .catch(() => {
          // ignora fallback automatico su lingua di default
        });

      return () => {
        isMounted = false;
      };
    }
  }, [scope, lang]);

  const activeDictionary = useMemo<Record<string, string>>(() => {
    const scopeData = dictionaryCache[scope] || {};
    // Ordine di risoluzione e fallback:
    // 1. Lingua attiva dell'utente (o dizionario caricato dinamicamente da API)
    // 2. Lingua inglese (en)
    // 3. Lingua italiana (it)
    // 4. Prima lingua disponibile trovata nello scope
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
    const scopeData = dictionaryCache[scope] || {};
    return scopeData['en'] || scopeData['it'] || {};
  }, [scope]);

  const { name: assistant } = useAssistantIdentity();

  const t = useCallback(
    (key: string, params?: Record<string, string | number>): string => {
      let text = activeDictionary[key] ?? fallbackDictionary[key] ?? key;
      const merged: Record<string, string | number> = { assistant, ...params };
      Object.entries(merged).forEach(([k, v]) => {
        text = text.split(`{${k}}`).join(String(v));
      });
      return text;
    },
    [activeDictionary, fallbackDictionary, assistant]
  );

  return { t, lang, setLang };
}

export function getScopedString(scope: string, lang: string, key: string, fallback?: string): string {
  const scopeData = dictionaryCache[scope];
  if (scopeData) {
    if (scopeData[lang] && scopeData[lang][key]) return scopeData[lang][key];
    if (scopeData['it'] && scopeData['it'][key]) return scopeData['it'][key];
    if (scopeData['en'] && scopeData['en'][key]) return scopeData['en'][key];
  }
  return fallback || key;
}
