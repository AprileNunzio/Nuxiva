import type { EngineManifest, EngineFamily } from './types';

const rawEngineManifests = import.meta.glob('/src/engines/**/manifest.json', { eager: true, import: 'default' });

export const engineRegistry: EngineManifest[] = Object.entries(rawEngineManifests).flatMap(([path, raw]) => {
  if (!raw || typeof raw !== 'object') return [];
  const manifest = raw as Partial<EngineManifest>;
  if (!manifest.id || !manifest.name || !manifest.family) return [];
  const scope = path.replace('/src/', '').replace('/manifest.json', '');
  return [{
    id: manifest.id,
    name: manifest.name,
    version: manifest.version || '1.0.0',
    family: manifest.family as EngineFamily,
    author: manifest.author || 'Nuxiva',
    scope,
    capabilities: manifest.capabilities || [],
    options: manifest.options || [],
  }];
});

export function getEnginesByFamily(family: EngineFamily): EngineManifest[] {
  return engineRegistry.filter((e) => e.family === family);
}

export function getEngineById(id: string): EngineManifest | undefined {
  return engineRegistry.find((e) => e.id === id);
}

export function getDefaultEngineForFamily(family: EngineFamily): string {
  const familyEngines = getEnginesByFamily(family);
  return familyEngines[0]?.id || '';
}
