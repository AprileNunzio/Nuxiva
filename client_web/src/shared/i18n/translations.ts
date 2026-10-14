import { it } from './locales/it';
import { en } from './locales/en';
import { fr } from './locales/fr';

export type SupportedLanguage = 'it' | 'en' | 'fr';

export const TRANSLATIONS = {
  it,
  en,
  fr,
} as const;

export type TranslationKey = keyof typeof TRANSLATIONS.it;
