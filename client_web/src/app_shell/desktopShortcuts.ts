import { useEffect, useState, useCallback } from 'react';
import { appRegistry } from './window_manager/registry';

const STORAGE_KEY = 'nuxiva_desktop_pinned_shortcuts';
const EVENT_NAME = 'nuxiva:desktop_shortcuts_updated';

// Scorciatoie di sistema di DEFAULT decise nel codice
export const DEFAULT_DESKTOP_IDS: readonly string[] = [
  'explorer',
  'applications',
  'games',
  'network',
  'features_hub',
  'updater',
];

function loadPinnedIds(): string[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((id) => typeof id === 'string') : [];
  } catch {
    return [];
  }
}

function savePinnedIds(ids: string[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
    window.dispatchEvent(new CustomEvent(EVENT_NAME, { detail: ids }));
  } catch {
    // Ignora errori di storage
  }
}

export function isPinnedToDesktop(appId: string): boolean {
  if (DEFAULT_DESKTOP_IDS.includes(appId)) return true;
  return loadPinnedIds().includes(appId);
}

export function isDefaultDesktopShortcut(appId: string): boolean {
  return DEFAULT_DESKTOP_IDS.includes(appId);
}

export function pinToDesktop(appId: string): void {
  if (DEFAULT_DESKTOP_IDS.includes(appId)) return;
  const current = loadPinnedIds();
  if (!current.includes(appId)) {
    savePinnedIds([...current, appId]);
  }
}

export function unpinFromDesktop(appId: string): void {
  if (DEFAULT_DESKTOP_IDS.includes(appId)) return;
  const current = loadPinnedIds();
  savePinnedIds(current.filter((id) => id !== appId));
}

export function toggleDesktopPin(appId: string): boolean {
  if (isPinnedToDesktop(appId)) {
    if (!isDefaultDesktopShortcut(appId)) {
      unpinFromDesktop(appId);
      return false;
    }
    return true;
  } else {
    pinToDesktop(appId);
    return true;
  }
}

export function useDesktopShortcuts() {
  const [pinnedIds, setPinnedIds] = useState<string[]>(loadPinnedIds);

  useEffect(() => {
    const handler = () => {
      setPinnedIds(loadPinnedIds());
    };
    window.addEventListener(EVENT_NAME, handler);
    window.addEventListener('storage', handler);
    return () => {
      window.removeEventListener(EVENT_NAME, handler);
      window.removeEventListener('storage', handler);
    };
  }, []);

  const allDesktopApps = useCallback(() => {
    // 1. App di default nell'ordine stabilito
    const defaultApps = DEFAULT_DESKTOP_IDS.map((id) =>
      appRegistry.find((app) => app.id === id)
    ).filter(Boolean) as typeof appRegistry;

    // 2. App personalizzate aggiunte dall'utente
    const customApps = pinnedIds
      .filter((id) => !DEFAULT_DESKTOP_IDS.includes(id))
      .map((id) => appRegistry.find((app) => app.id === id))
      .filter(Boolean) as typeof appRegistry;

    return [...defaultApps, ...customApps];
  }, [pinnedIds]);

  return {
    shortcuts: allDesktopApps(),
    pinnedIds,
    pin: pinToDesktop,
    unpin: unpinFromDesktop,
    togglePin: toggleDesktopPin,
    isPinned: isPinnedToDesktop,
    isDefault: isDefaultDesktopShortcut,
  };
}
