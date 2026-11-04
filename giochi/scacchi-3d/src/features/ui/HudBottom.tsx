import { useState, useEffect } from 'react';
import { i18n } from '../i18n/i18nService';
import { TranslationDictionary } from '../i18n/types';

export function HudBottom() {
  const [dict, setDict] = useState<TranslationDictionary>(i18n.getDictionary());

  useEffect(() => {
    return i18n.subscribe((_, newDict) => {
      setDict(newDict);
    });
  }, []);

  return (
    <div id="hud-bottom">
      <div className="hint-pill" id="controls-hint">
        {dict.controls.desktopHint}
      </div>
      <div className="captured-pill" id="captured-tray"></div>
    </div>
  );
}
