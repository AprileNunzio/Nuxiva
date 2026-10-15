import { it } from './locales/it';
import { en } from './locales/en';
import { fr } from './locales/fr';
import { es } from './locales/es';

export type SupportedLanguage = 'it' | 'en' | 'fr' | 'es';

export const TRANSLATIONS = {
  it,
  en,
  fr,
  es,
} as const;

export type TranslationKey = keyof typeof TRANSLATIONS.it;
