import { SupportedLocale, TranslationDictionary } from './types';
import { it } from './locales/it';
import { en } from './locales/en';

const dictionaries: Record<SupportedLocale, TranslationDictionary> = {
  it,
  en
};

type Listener = (locale: SupportedLocale, dict: TranslationDictionary) => void;

class I18nService {
  private static instance: I18nService;
  private currentLocale: SupportedLocale = 'it';
  private listeners: Set<Listener> = new Set();

  private constructor() {
    const saved = typeof window !== 'undefined' ? localStorage.getItem('app_locale') : null;
    if (saved === 'it' || saved === 'en') {
      this.currentLocale = saved;
    } else if (typeof navigator !== 'undefined' && navigator.language?.startsWith('en')) {
      this.currentLocale = 'en';
    } else {
      this.currentLocale = 'it';
    }
  }

  public static getInstance(): I18nService {
    if (!I18nService.instance) {
      I18nService.instance = new I18nService();
    }
    return I18nService.instance;
  }

  public getLocale(): SupportedLocale {
    return this.currentLocale;
  }

  public getDictionary(): TranslationDictionary {
    return dictionaries[this.currentLocale];
  }

  public setLocale(locale: SupportedLocale): void {
    if (this.currentLocale === locale) return;
    this.currentLocale = locale;
    if (typeof window !== 'undefined') {
      localStorage.setItem('app_locale', locale);
    }
    this.notify();
  }

  public subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    listener(this.currentLocale, this.getDictionary());
    return () => {
      this.listeners.delete(listener);
    };
  }

  private notify(): void {
    const dict = this.getDictionary();
    for (const listener of this.listeners) {
      listener(this.currentLocale, dict);
    }
  }
}

export const i18n = I18nService.getInstance();
