import { appRegistry } from './registry';
import type { AppManifest } from './types';

export type AppKind = 'app' | 'feature' | 'system';

/**
 * Applicazioni autonome del sistema Nuxiva:
 * Programmi completi con interfaccia di lavoro, riproduzione, visualizzazione o gestione file.
 */
const KNOWN_APPLICATION_IDS = new Set([
  'music',        // Nexus Media Player (musica, video, karaoke)
  'iptv',         // TV & IPTV (canali live, EPG, tuner)
  'explorer',     // Assistente / Gestione file e condivisioni SMB
  'applications', // Catalogo Applicazioni
  'studio_3d',    // Visualizzatore e Studio Modelli 3D
  'terminal',     // Terminale e riga di comando
  'system_logs',  // Visualizzatore log ed eventi
  'home_assistant', // Home Assistant (gestione dispositivi, stanze, consumi, assist)
  'voice_studio', // Studio delle Voci (sintesi, equalizzatore, clonazione microfonica)
  'network',      // Rete & Mesh (dispositivi, satelliti, PC)
  'repair_workbench',
  'ollama',
]);

/**
 * ID riservati o interni dell'infrastruttura di sistema
 */
const SYSTEM_INTERNAL_IDS = new Set([
  'features_hub',
  'feature_settings',
]);

/**
 * Determina se un elemento è una vera Applicazione autonoma.
 */
export function isApplication(item: { id: string; scope?: string; kind?: string }): boolean {
  if (item.kind === 'app') return true;
  if (item.kind === 'feature') return false;
  if (item.scope?.startsWith('apps/')) return true;
  if (KNOWN_APPLICATION_IDS.has(item.id)) return true;
  return false;
}

/**
 * Determina se un elemento è una Funzionalità (opzione/modulo di sistema).
 */
export function isFeature(item: { id: string; scope?: string; kind?: string }): boolean {
  if (item.kind === 'feature') return true;
  if (item.kind === 'app') return false;
  if (SYSTEM_INTERNAL_IDS.has(item.id)) return false;
  return !isApplication(item);
}

/**
 * Scanner del registro: restituisce tutte le Applicazioni registrate.
 */
export function getRegisteredApplications(): typeof appRegistry {
  return appRegistry.filter(
    (app) => app.target !== 'node' && isApplication(app) && app.id !== 'applications'
  );
}

/**
 * Scanner del registro: restituisce tutte le Funzionalità registrate.
 */
export function getRegisteredFeatures(): typeof appRegistry {
  return appRegistry.filter(
    (app) => app.target !== 'node' && isFeature(app)
  );
}
