import { useScopedI18n } from '../../../shared/i18n/useScopedI18n';

export const BRAIN_SCOPE = 'features/brain_center';

export type Translate = (key: string, params?: Record<string, string | number>) => string;

export const useBrainText = () => useScopedI18n(BRAIN_SCOPE);

export const useSectionText = (section: string) => useScopedI18n(`${BRAIN_SCOPE}/sections/${section}`);
