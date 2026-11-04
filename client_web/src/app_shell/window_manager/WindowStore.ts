import { useSyncExternalStore } from 'react';
import { resolveApp } from './registry';
import type { OSWindow, OSWindowOpenRequest } from './types';

let storageKey: string | null = null;
let preferences: Record<string, Partial<OSWindow>> = {};
const listeners = new Set<() => void>();
const modes = ['floating', 'maximized', 'snapped-left', 'snapped-right', 'quarter-tl', 'quarter-tr', 'quarter-bl', 'quarter-br'];
function initialGeometry(app: NonNullable<ReturnType<typeof resolveApp>>) {
  const host = typeof document !== 'undefined' ? document.querySelector('.os-workspace') : null;
  const bounds = host?.getBoundingClientRect();
  const rem = bounds ? parseFloat(getComputedStyle(document.documentElement).fontSize) : 0;
  if(app.window?.units==='px')return {
    width:bounds?Math.min(100,Math.max(1,(app.window.defaultWidth || 960)/bounds.width*100)):65,
    height:bounds?Math.min(100,Math.max(1,(app.window.defaultHeight || 640)/bounds.height*100)):75,
  };
  return {
    width: bounds && bounds.width / rem < 52 ? 96 : Math.max(1, Math.min(100, app.window?.defaultWidth || 65, bounds?.width ? (app.window?.defaultWidth || 65) * rem / bounds.width * 100 : 100)),
    height: Math.max(1, Math.min(100, app.window?.defaultHeight || 75, bounds?.height ? 48 * rem / bounds.height * 100 : 100)),
  };
}
function restore(): OSWindow[] {
  try {
    const saved = JSON.parse(storageKey ? localStorage.getItem(storageKey) || '[]' : '[]');
    if (!Array.isArray(saved)) return [];
    return saved.slice(0, 100).filter(w => w && typeof w.id === 'string' && resolveApp(w.appId) &&
      ['x', 'y', 'width', 'height', 'z'].every(k => Number.isFinite(w[k])) &&
      w.width > 0 && w.width <= 100 && w.height > 0 && w.height <= 100 &&
      (!w.windowMode || modes.includes(w.windowMode)) &&
      (!w.targetNodeId || typeof w.targetNodeId === 'string'))
      .map(({ forcedLocale, ...w }, index) => {
        const limits = initialGeometry(resolveApp(w.appId)!);
        const width = w.layoutVersion === 2 ? w.width : Math.min(w.width,limits.width);
        const height = w.layoutVersion === 2 ? w.height : Math.min(w.height,limits.height);
        return { ...w, width, height, layoutVersion:2, z:index+1, minimized:!!w.minimized, pinned:!!w.pinned, initialPayload:undefined, x:Math.max(0,Math.min(100-width,w.x)), y:Math.max(0,Math.min(100-height,w.y)) };
      });
  } catch { return []; }
}
let windows: OSWindow[] = [];
let sequence = Math.max(0, ...windows.map(w => w.z));
function commit(next: OSWindow[]) {
  windows = next;
  try { if (storageKey) localStorage.setItem(storageKey, JSON.stringify(windows.map(({ initialPayload, ...w }) => w))); } catch { /* workspace remains usable without storage */ }
  listeners.forEach(fn => fn());
}
export const windowStore = {
  activateWorkspace(user: string) {
    storageKey = `nuxiva.workspace.v1:${encodeURIComponent(user)}`;
    try { const saved = JSON.parse(localStorage.getItem(`${storageKey}:preferences`) || '{}'); preferences = saved && typeof saved === 'object' && !Array.isArray(saved) ? saved : {}; } catch { preferences = {}; }
    windows = restore();
    sequence = Math.max(0, ...windows.map(w => w.z));
    listeners.forEach(fn => fn());
  },
  releaseWorkspace() { storageKey = null; preferences = {}; windows = []; listeners.forEach(fn => fn()); },
  openWindow(input: OSWindowOpenRequest): string {
    const request: OSWindowOpenRequest = { appId:input.appId,instanceKey:input.instanceKey,targetNodeId:input.targetNodeId,initialPayload:input.initialPayload,windowMode:input.windowMode };
    const app = resolveApp(request.appId);
    if (!app) throw new Error(`Unknown OS app: ${request.appId}`);
    if (request.windowMode && !modes.includes(request.windowMode)) throw new Error('Invalid window mode');
    const existing = windows.find(w => w.appId === app.id && (app.window?.singleton===true||w.instanceKey === request.instanceKey) && w.targetNodeId === request.targetNodeId);
    if (existing) {
      this.update(existing.id, { ...request, windowMode:request.windowMode || existing.windowMode, appId: app.id, minimized: false, z: ++sequence });
      return existing.id;
    }
    // randomUUID is HTTPS-only; getRandomValues also works on an HTTP LAN.
    const id = typeof crypto.randomUUID === 'function' ? crypto.randomUUID()
      : Array.from(crypto.getRandomValues(new Uint8Array(16)), byte => byte.toString(16).padStart(2, '0')).join('');
    const { width, height } = initialGeometry(app);
    const offset = 3 + (windows.length % 6) * 3;
    const saved = preferences[app.id] || {};
    const geometry = ['x','y','width','height'].every(key => Number.isFinite(saved[key]) && saved[key] >= 0 && saved[key] <= 100) && saved.width! > 0 && saved.height! > 0 ? { x:Math.min(saved.x!,100-saved.width!),y:Math.min(saved.y!,100-saved.height!),width:saved.width!,height:saved.height! } : {};
    const windowMode = request.windowMode || (modes.includes(saved.windowMode || '') ? saved.windowMode : 'maximized');
    commit([...windows, { ...request, appId: app.id, id, layoutVersion:2, width, height, x: Math.min(offset, 100-width), y: Math.min(offset, 100-height), ...geometry, windowMode, minimized: false, pinned: false, z: ++sequence }]);
    return id;
  },
  update(id: string, patch: Partial<OSWindow>) {
    const current = windows.find(w => w.id === id);
    if (current && ['windowMode','x','y','width','height'].some(key => patch[key] !== undefined)) {
      const next = { ...current, ...patch };
      preferences[current.appId] = { windowMode:next.windowMode, x:next.x,y:next.y,width:next.width,height:next.height };
      try { if (storageKey) localStorage.setItem(`${storageKey}:preferences`, JSON.stringify(preferences)); } catch { /* storage is optional */ }
    }
    commit(windows.map(w => w.id === id ? { ...w, ...patch, id: w.id, appId: w.appId } : w));
  },
  focus(id: string) { this.update(id, { z: ++sequence, minimized: false }); },
  close(id: string) { commit(windows.filter(w => w.id !== id)); },
  closeAll() { commit([]); },
};
export function useWindowStore() {
  return useSyncExternalStore(fn => { listeners.add(fn); return () => { listeners.delete(fn); }; }, () => windows);
}
declare global { interface Window { NuxivaOS: typeof windowStore } }
window.NuxivaOS = windowStore;
