import { useState, useEffect } from 'react';
import { i18n } from '../i18n/i18nService';
import { SupportedLocale } from '../i18n/types';

export function LanguageSwitcher() {
  const [locale, setLocale] = useState<SupportedLocale>(i18n.getLocale());

  useEffect(() => {
    return i18n.subscribe((newLocale) => {
      setLocale(newLocale);
    });
  }, []);

  const toggleLocale = () => {
    const next = locale === 'it' ? 'en' : 'it';
    i18n.setLocale(next);
  };

  return (
    <button
      type="button"
      className="hud-btn"
      onClick={toggleLocale}
      title="Switch Language / Cambia Lingua"
      style={{
        padding: '6px 12px',
        fontWeight: 700,
        letterSpacing: '0.05em',
        minWidth: '42px'
      }}
    >
      {locale.toUpperCase()}
    </button>
  );
}
