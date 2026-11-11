import type { EcosystemManifest, EcosystemKind } from './types';

const agentManifests = import.meta.glob('/src/agents/**/manifest.json', { eager: true, import: 'default' });
const skillManifests = import.meta.glob('/src/skills/**/manifest.json', { eager: true, import: 'default' });
const pluginManifests = import.meta.glob('/src/plugins/**/manifest.json', { eager: true, import: 'default' });
const brainManifests = import.meta.glob('/src/brains/**/manifest.json', { eager: true, import: 'default' });

function parseManifests(records: Record<string, unknown>, defaultKind: EcosystemKind): EcosystemManifest[] {
  return Object.entries(records).flatMap(([path, raw]) => {
    if (!raw || typeof raw !== 'object') return [];
    const manifest = raw as Partial<EcosystemManifest>;
    if (!manifest.id || !manifest.name) return [];
    const scope = path.replace('/src/', '').replace('/manifest.json', '');
    return [{
      id: manifest.id,
      name: manifest.name,
      version: manifest.version || '1.0.0',
      kind: (manifest.kind as EcosystemKind) || defaultKind,
      author: manifest.author || 'Nuxiva',
      role: manifest.role,
      family: manifest.family,
      scope,
      placement: manifest.placement,
      capabilities: manifest.capabilities || [],
      options: manifest.options || [],
    }];
  });
}

export const registeredAgents: EcosystemManifest[] = parseManifests(agentManifests, 'agent');
export const registeredSkills: EcosystemManifest[] = parseManifests(skillManifests, 'skill');
export const registeredPlugins: EcosystemManifest[] = parseManifests(pluginManifests, 'plugin');
export const registeredBrains: EcosystemManifest[] = parseManifests(brainManifests, 'brain');

export const allEcosystemEntities: EcosystemManifest[] = [
  ...registeredAgents,
  ...registeredSkills,
  ...registeredPlugins,
  ...registeredBrains,
];

export function getAgents(): EcosystemManifest[] {
  return registeredAgents;
}

export function getSkills(): EcosystemManifest[] {
  return registeredSkills;
}

export function getPlugins(): EcosystemManifest[] {
  return registeredPlugins;
}

export function getBrains(): EcosystemManifest[] {
  return registeredBrains;
}

export function getEcosystemEntityById(id: string): EcosystemManifest | undefined {
  return allEcosystemEntities.find((e) => e.id === id);
}

export function getEcosystemEntitiesByKind(kind: EcosystemKind): EcosystemManifest[] {
  return allEcosystemEntities.filter((e) => e.kind === kind);
}
