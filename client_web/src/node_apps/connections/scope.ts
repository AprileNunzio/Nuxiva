import { useScopedI18n } from '../../shared/i18n/useScopedI18n';

export const CONNECTIONS_SCOPE = 'node_apps/connections';

export function useConnectionsI18n() {
  return useScopedI18n(CONNECTIONS_SCOPE);
}
