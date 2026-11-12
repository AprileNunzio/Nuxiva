import { useState, useEffect } from 'react';
import { i18n } from '../i18n/i18nService';
import { TranslationDictionary } from '../i18n/types';

export function LoadingOverlay() {
  const [dict, setDict] = useState<TranslationDictionary>(i18n.getDictionary());

  useEffect(() => {
    return i18n.subscribe((_, newDict) => {
      setDict(newDict);
    });
  }, []);

  return (
    <div id="loading-overlay">
      <div className="loader-title">{dict.brand.loadingTitle}</div>
      <div className="loader-bar-wrap">
        <div className="loader-bar" id="loader-bar"></div>
      </div>
      <div id="loader-text">{dict.brand.loadingSubtitle}</div>
    </div>
  );
}
