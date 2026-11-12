import { useScopedI18n } from '../../shared/i18n/useScopedI18n';

export function useFascicoliI18n() {
  return useScopedI18n('apps/fascicoli');
}

export const KNOWN_PROBLEMS = new Set(['edited', 'missing', 'unlogged', 'chain_broken', 'should_be_pruned', 'unknown_entry']);
export const KNOWN_LEVELS = new Set(['lampo', 'standard', 'progetto']);

export const segments = (rel: string): string => rel.split('/').map(encodeURIComponent).join('/');
