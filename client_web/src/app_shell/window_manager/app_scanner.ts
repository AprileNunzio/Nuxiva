import { appRegistry } from './registry';
import type { AppManifest } from './types';

export type AppKind = 'app' | 'feature' | 'system';

export const KNOWN_APPLICATION_IDS = new Set<string>([]);

export function isSubapp(item: { id?: string; scope?: string; isSubapp?: boolean; parent?: string }): boolean {
  if (item.isSubapp === true) return true;
  if (typeof item.parent === 'string' && item.parent.length > 0) return true;
  if (typeof item.scope === 'string' && item.scope.startsWith('subapps/') && item.scope.split('/').length >= 3) return true;
  return false;
}

export function isApplication(item: {
  id: string;
  scope?: string;
  kind?: string;
  isSubapp?: boolean;
  parent?: string;
  category?: string;
  launcher?: boolean;
  target?: string;
}): boolean {
  if (item.target === 'node') return false;
  if (item.launcher === false) return false;
  if (item.id === 'applications' || item.id === 'feature_settings') return false;
  if (item.kind === 'feature') return false;
  return true;
}

export function isFeature(item: {
  id: string;
  scope?: string;
  kind?: string;
  isSubapp?: boolean;
  parent?: string;
  category?: string;
  launcher?: boolean;
  target?: string;
}): boolean {
  if (item.target === 'node') return false;
  if (item.kind === 'feature') return true;
  if (item.id === 'features_hub' || item.id === 'feature_settings') return false;
  return !isApplication(item);
}

export function getRegisteredApplications(includeSubapps = true): typeof appRegistry {
  return appRegistry.filter((app) => {
    if (app.target === 'node') return false;
    if (app.launcher === false) return false;
    if (app.id === 'applications' || app.id === 'feature_settings') return false;
    if (!includeSubapps && isSubapp(app)) return false;
    return isApplication(app);
  });
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
