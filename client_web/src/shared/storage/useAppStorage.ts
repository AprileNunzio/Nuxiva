import { useState, useEffect, useCallback, useContext } from 'react';
import { createScopedStorage, ScopedStorage } from './scopedStorage';
import { WindowContext } from '../../app_shell/window_manager/WindowContext';

export function useAppStorage<T>(
  key: string,
  initialValue: T,
  explicitAppId?: string
): [T, (val: T | ((prev: T) => T)) => boolean, () => void, ScopedStorage] {
  const windowCtx = useContext(WindowContext);
  const appId = explicitAppId || windowCtx?.appId || 'system_shared';
  const storage = createScopedStorage(appId);

  const [storedValue, setStoredValue] = useState<T>(() => {
    const item = storage.getItem<T>(key);
    return item !== null ? item : initialValue;
  });

  useEffect(() => {
    const handleStorageChange = (e: Event) => {
      const customEvent = e as CustomEvent<{ appId: string; key: string; value: unknown }>;
      if (
        customEvent.detail &&
        customEvent.detail.appId === appId &&
        (customEvent.detail.key === key || customEvent.detail.key === '*')
      ) {
        const updated = storage.getItem<T>(key);
        setStoredValue(updated !== null ? updated : initialValue);
      }
    };

    window.addEventListener('nuxiva:scoped-storage', handleStorageChange);
    return () => {
      window.removeEventListener('nuxiva:scoped-storage', handleStorageChange);
    };
  }, [appId, key, initialValue]);

  const setValue = useCallback(
    (value: T | ((prev: T) => T)): boolean => {
      const valueToStore = value instanceof Function ? value(storedValue) : value;
      const success = storage.setItem(key, valueToStore);
      if (success) {
        setStoredValue(valueToStore);
      }
      return success;
    },
    [key, storage, storedValue]
  );

  const removeValue = useCallback(() => {
    storage.removeItem(key);
    setStoredValue(initialValue);
  }, [key, storage, initialValue]);

  return [storedValue, setValue, removeValue, storage];
}
