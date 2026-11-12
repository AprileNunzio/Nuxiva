import type { OSWindow } from './window_manager/types';
export function taskbarGroups(windows: readonly OSWindow[], pinned: readonly string[]) {
  return [...new Set([...pinned, ...windows.map(window => window.appId)])].map(appId => {
    const entries = windows.filter(window => window.appId === appId).sort((a,b)=>b.z-a.z);
    return { appId, entries, background:entries.length > 0 && entries.every(window => window.minimized) };
  });
}
