import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { STATUSES } from './types';

export function useProgettiI18n() {
  return useScopedI18n('apps/progetti');
}

export const isStatus = (value: string): boolean => (STATUSES as readonly string[]).includes(value);

export const canPause = (status: string): boolean => ['planning', 'running', 'waiting_user'].includes(status);
export const canResume = (status: string): boolean => status === 'paused';
export const canCancel = (status: string): boolean => !['completed', 'failed', 'cancelled'].includes(status);
export const canArchive = (status: string): boolean => ['paused', 'completed', 'failed', 'cancelled'].includes(status);
export const canDelete = (status: string): boolean => status !== 'running';
