import { useScopedI18n } from '../../shared/i18n/useScopedI18n';

export const TASK_MANAGER_SCOPE = 'node_apps/task_manager';

export function useTaskManagerI18n() {
  return useScopedI18n(TASK_MANAGER_SCOPE);
}