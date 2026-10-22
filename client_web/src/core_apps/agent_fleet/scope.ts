import { NodeModuleError } from '../../node_apps/shared/data/http';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';

export function useFleetI18n() {
  return useScopedI18n('core_apps/agent_fleet');
}

export const fieldClass =
  'w-full rounded-xl border border-slate-700 bg-slate-950/70 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-cyan-400/70 focus-visible:ring-2 focus-visible:ring-cyan-400/40 disabled:opacity-50';

export const KNOWN_ERRORS = new Set([
  'exists', 'invalid_id', 'invalid_name', 'invalid_kind', 'invalid_category', 'invalid_state', 'invalid_priority', 'invalid_body', 'invalid_filter',
  'invalid_cursor', 'invalid_ref', 'invalid_link_kind', 'unknown_tool', 'unknown_widget', 'not_found', 'too_many_links', 'too_many',
]);

export function errorKey(cause: unknown): string {
  return cause instanceof NodeModuleError && KNOWN_ERRORS.has(cause.code) ? `error_${cause.code}` : 'error_generic';
}
