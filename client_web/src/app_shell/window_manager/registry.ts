import React, { lazy } from 'react';
import type { AppManifest } from './types';
import { normalizeManifest } from './normalizeManifest';

const manifests = import.meta.glob('/src/**/manifest.json', { eager: true, import: 'default' });
const views = import.meta.glob('/src/**/View.tsx');
const icons = import.meta.glob('/src/**/*.{png,webp,avif,svg}', { eager: true, query: '?url', import: 'default' });
export const appRegistry = Object.entries(manifests).flatMap(([path, raw]) => {
  const view = views[path.replace('manifest.json', 'View.tsx')];
  if (!view) return [];
  const scope = path.replace('/src/', '').replace('/manifest.json', '');
  const manifest = normalizeManifest(raw,scope) as AppManifest | null;
  if(!manifest)return [];
  const id = manifest.target === 'node' ? scope : manifest.id;
  const iconPath = path.replace('manifest.json', (manifest.icon3d || './icon.png').replace(/^\.\//,''));
  return [{ ...manifest, id, scope, iconUrl: icons[iconPath] as string | undefined, Component: lazy(async () => {
    const module = await view() as { View: React.ComponentType<any> };
    return { default: module.View };
  }) }];
});
export function resolveApp(id: string) {
  return appRegistry.find(app => app.id === id || app.scope === id);
}
