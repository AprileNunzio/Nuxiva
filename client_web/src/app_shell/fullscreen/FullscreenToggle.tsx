import React from 'react';
import { Expand, Shrink } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { useFullscreen } from './useFullscreen';
import './fullscreen.css';

export function FullscreenToggle() {
  const { t } = useScopedI18n('app_shell/fullscreen');
  const { available, active, toggle } = useFullscreen();
  if (!available) return null;
  const label = t(active ? 'exit' : 'enter');
  return (
    <button
      type="button"
      className="os-fullscreen-toggle"
      data-active={active}
      aria-pressed={active}
      aria-label={label}
      title={label}
      onClick={event => {
        event.stopPropagation();
        void toggle();
      }}
    >
      <span className="os-fullscreen-glyph" aria-hidden="true">{active ? <Shrink /> : <Expand />}</span>
      <span className="os-fullscreen-hint" aria-hidden="true">{label}</span>
    </button>
  );
}
