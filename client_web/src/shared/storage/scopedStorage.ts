const MAX_APP_STORAGE_BYTES = 5 * 1024 * 1024;
const PREFIX = 'nuxiva:app:';

export interface ScopedStorage {
  getItem: <T = string>(key: string) => T | null;
  setItem: <T>(key: string, value: T) => boolean;
  removeItem: (key: string) => void;
  clear: () => void;
  getAllKeys: () => string[];
  getStorageUsage: () => { usedBytes: number; maxBytes: number; percent: number };
}

function getAppPrefix(appId: string): string {
  const sanitized = appId.replace(/[^a-zA-Z0-9_-]/g, '_');
  return `${PREFIX}${sanitized}:`;
}

export function createScopedStorage(appId: string): ScopedStorage {
  const appPrefix = getAppPrefix(appId);

  return {
    getItem: <T = string>(key: string): T | null => {
      try {
        const fullKey = `${appPrefix}${key}`;
        const raw = window.localStorage.getItem(fullKey);
        if (raw === null) return null;
        try {
          return JSON.parse(raw) as T;
        } catch {
          return raw as unknown as T;
        }
      } catch {
        return null;
      }
    },

    setItem: <T>(key: string, value: T): boolean => {
      try {
        const fullKey = `${appPrefix}${key}`;
        const serialized = typeof value === 'string' ? value : JSON.stringify(value);
        let currentAppBytes = 0;
        for (let i = 0; i < window.localStorage.length; i++) {
          const k = window.localStorage.key(i);
          if (k && k.startsWith(appPrefix) && k !== fullKey) {
            const v = window.localStorage.getItem(k);
            if (v) currentAppBytes += k.length + v.length;
          }
        }
        const incomingBytes = fullKey.length + serialized.length;
        if (currentAppBytes + incomingBytes > MAX_APP_STORAGE_BYTES) {
          return false;
        }
        window.localStorage.setItem(fullKey, serialized);
        window.dispatchEvent(new window.CustomEvent('nuxiva:scoped-storage', {
          detail: { appId, key, value }
        }));
        return true;
      } catch {
        return false;
      }
    },

    removeItem: (key: string): void => {
      try {
        const fullKey = `${appPrefix}${key}`;
        window.localStorage.removeItem(fullKey);
        window.dispatchEvent(new window.CustomEvent('nuxiva:scoped-storage', {
          detail: { appId, key, value: null }
        }));
      } catch {}
    },

    clear: (): void => {
      try {
        const keysToRemove: string[] = [];
        for (let i = 0; i < window.localStorage.length; i++) {
          const k = window.localStorage.key(i);
          if (k && k.startsWith(appPrefix)) {
            keysToRemove.push(k);
          }
        }
        for (const k of keysToRemove) {
          window.localStorage.removeItem(k);
        }
        window.dispatchEvent(new window.CustomEvent('nuxiva:scoped-storage', {
          detail: { appId, key: '*', value: null }
        }));
      } catch {}
    },

    getAllKeys: (): string[] => {
      try {
        const result: string[] = [];
        for (let i = 0; i < window.localStorage.length; i++) {
          const k = window.localStorage.key(i);
          if (k && k.startsWith(appPrefix)) {
            result.push(k.slice(appPrefix.length));
          }
        }
        return result;
      } catch {
        return [];
      }
    },

    getStorageUsage: (): { usedBytes: number; maxBytes: number; percent: number } => {
      try {
        let used = 0;
        for (let i = 0; i < window.localStorage.length; i++) {
          const k = window.localStorage.key(i);
          if (k && k.startsWith(appPrefix)) {
            const v = window.localStorage.getItem(k);
            if (v) used += k.length + v.length;
          }
        }
        const percent = Math.min(100, Math.round((used / MAX_APP_STORAGE_BYTES) * 100));
        return { usedBytes: used, maxBytes: MAX_APP_STORAGE_BYTES, percent };
      } catch {
        return { usedBytes: 0, maxBytes: MAX_APP_STORAGE_BYTES, percent: 0 };
      }
    }
  };
}
