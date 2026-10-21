import React, { createContext, useContext, useState, useEffect } from 'react';
import { SupportedLanguage, TRANSLATIONS, TranslationKey } from './translations';
import { availableLanguages } from './languageRegistry';

interface I18nContextType {
  lang: SupportedLanguage;
  setLang: (lang: SupportedLanguage) => void;
  t: (key: TranslationKey) => string;
}

const I18nContext = createContext<I18nContextType | null>(null);

export const I18nProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [lang, setLangState] = useState<SupportedLanguage>(() => {
    const saved = localStorage.getItem('nuxiva_ui_lang');
    if (availableLanguages.includes(saved)) {
      return saved;
    }
    const nav = navigator.language.slice(0, 2).toLowerCase();
    if (availableLanguages.includes(nav)) return nav;
    return availableLanguages.includes('it') ? 'it' : availableLanguages[0] || 'en';
  });

  const setLang = (newLang: SupportedLanguage) => {
    setLangState(newLang);
    localStorage.setItem('nuxiva_ui_lang', newLang);
  };

  const t = (key: TranslationKey): string => {
    const dict = TRANSLATIONS[lang] || TRANSLATIONS.it;
    return dict[key] || TRANSLATIONS.it[key] || key;
  };

  return (
    <I18nContext.Provider value={{ lang, setLang, t }}>
      {children}
    </I18nContext.Provider>
  );
};

export const useI18n = (): I18nContextType => {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    throw new Error('useI18n must be used within an I18nProvider');
  }
  return ctx;
};

/** Nested provider: a window locale never changes the desktop preference. */
export const ScopedI18nProvider: React.FC<{
  lang: SupportedLanguage;
  onChange: (lang: SupportedLanguage) => void;
  children: React.ReactNode;
}> = ({ lang, onChange, children }) => (
  <I18nContext.Provider value={{ lang, setLang: onChange, t: (key) => TRANSLATIONS[lang]?.[key] || TRANSLATIONS.it[key] || key }}>
    {children}
  </I18nContext.Provider>
);
