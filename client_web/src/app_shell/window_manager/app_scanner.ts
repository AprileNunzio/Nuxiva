import { appRegistry } from './registry';
import type { AppManifest } from './types';

export type AppKind = 'app' | 'feature' | 'system';

const KNOWN_APPLICATION_IDS = new Set([
  'music',
  'iptv',
  'explorer',
  'applications',
  'studio_3d',
  'terminal',
  'system_logs',
  'home_assistant',
  'voice_studio',
  'network',
  'repair_workbench',
  'ollama',
  'giochi',
  'videosorveglianza',
]);

const SYSTEM_INTERNAL_IDS = new Set([
  'features_hub',
  'feature_settings',
]);

export function isSubapp(item: { id?: string; scope?: string; isSubapp?: boolean; parent?: string }): boolean {
  if (item.isSubapp === true) return true;
  if (typeof item.parent === 'string' && item.parent.length > 0) return true;
  if (typeof item.scope === 'string' && item.scope.startsWith('subapps/') && item.scope.split('/').length >= 3) return true;
  return false;
}

export function isApplication(item: { id: string; scope?: string; kind?: string; isSubapp?: boolean; parent?: string }): boolean {
  if (isSubapp(item)) return true;
  if (item.kind === 'app') return true;
  if (item.kind === 'feature') return false;
  if (item.scope?.startsWith('apps/') || item.scope?.startsWith('subapps/')) return true;
  if (KNOWN_APPLICATION_IDS.has(item.id)) return true;
  return false;
}

export function isFeature(item: { id: string; scope?: string; kind?: string; isSubapp?: boolean; parent?: string }): boolean {
  if (isSubapp(item)) return false;
  if (item.kind === 'feature') return true;
  if (item.kind === 'app') return false;
  if (SYSTEM_INTERNAL_IDS.has(item.id)) return false;
  return !isApplication(item);
}

export function getRegisteredApplications(): typeof appRegistry {
  return appRegistry.filter(
    (app) => app.target !== 'node' && isApplication(app) && app.id !== 'applications' && !isSubapp(app)
  );
}

export function getRegisteredFeatures(): typeof appRegistry {
  return appRegistry.filter(
    (app) => app.target !== 'node' && isFeature(app)
  );
}

export function getSubapps(parentId: string): typeof appRegistry {
  return appRegistry.filter(
    (app) => isSubapp(app) && (app.parent === parentId || app.scope?.startsWith(`subapps/${parentId}/`))
  );
}

export function getParentApp(subappId: string): typeof appRegistry[number] | undefined {
  const sub = appRegistry.find((app) => app.id === subappId);
  if (!sub || !isSubapp(sub)) return undefined;
  const parentId = sub.parent || (sub.scope?.startsWith('subapps/') ? sub.scope.split('/')[1] : undefined);
  if (!parentId) return undefined;
  return appRegistry.find((app) => app.id === parentId);
}
