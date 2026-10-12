import React, { createContext, useContext, useState, useEffect } from 'react';
import { SupportedLanguage, TRANSLATIONS, TranslationKey } from './translations';

interface I18nContextType {
  lang: SupportedLanguage;
  setLang: (lang: SupportedLanguage) => void;
  t: (key: TranslationKey) => string;
}

const I18nContext = createContext<I18nContextType | null>(null);

export const I18nProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [lang, setLangState] = useState<SupportedLanguage>(() => {
    const saved = localStorage.getItem('nuxiva_ui_lang');
    if (saved === 'it' || saved === 'en' || saved === 'fr') {
      return saved;
    }
    const nav = navigator.language.slice(0, 2).toLowerCase();
    if (nav === 'it' || nav === 'fr') return nav;
    return 'it'; 
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
