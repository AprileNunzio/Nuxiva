import React from 'react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { useLiveCaptions } from './useLiveCaptions';
import './live_captions.css';

export const LiveCaptionsOverlay: React.FC = () => {
  const { lines, config } = useLiveCaptions();
  const { t } = useScopedI18n('live_captions');

  if (!config.enabled || lines.length === 0) {
    return null;
  }

  return (
    <aside
      className="nx-live-captions"
      data-size={config.size}
      data-position={config.position}
      role="log"
      aria-live="polite"
    >
      {lines.map((line) => {
        const showSpeaker = config.speaker && (Boolean(line.speakerName) || line.final);
        const displayName = line.speakerName || t('cap_unknown');
        const style = { '--cap-hue': line.speakerHue } as React.CSSProperties;
        const classes = [
          'nx-cap',
          line.addressed ? 'addressed' : '',
          line.done ? 'done' : ''
        ].filter(Boolean).join(' ');

        return (
          <div key={line.utt} className={classes} style={style}>
            {showSpeaker && (
              <span className="nx-cap-who">
                <span className="nx-cap-who-dot" />
                {displayName}
              </span>
            )}
            <span className="nx-cap-text">
              {line.words.map((word, idx) => (
                <span
                  key={`${line.utt}-${idx}-${word.text}`}
                  className={`nx-cap-w ${word.stable ? 'stable' : 'in'}`}
                >
                  {word.text}{' '}
                </span>
              ))}
            </span>
          </div>
        );
      })}
    </aside>
  );
};
