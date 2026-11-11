import React from 'react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { Panel, Btn, Empty } from '../shared/kit';
import { Video, Compass } from 'lucide-react';

interface PtzPanelProps {
  hasPtzCam: boolean;
  pan: number;
  tilt: number;
  zoom: number;
  onMove: (pan: number, tilt: number, zoom: number) => void;
}

export const PtzPanel: React.FC<PtzPanelProps> = ({
  hasPtzCam,
  pan,
  tilt,
  zoom,
  onMove,
}) => {
  const { t } = useScopedI18n('apps/matter');

  if (!hasPtzCam) {
    return (
      <Panel title={t('tab_ptz')}>
        <Empty>{t('no_ptz_cameras')}</Empty>
      </Panel>
    );
  }

  return (
    <Panel title={t('tab_ptz')}>
      <div className="flex flex-col gap-4 max-w-md">
        <div className="flex items-center gap-2">
          <Video className="h-4 w-4 text-primary" />
          <span className="font-semibold text-sm">Controllo Movimento 360° Real-time</span>
        </div>

        <div className="flex flex-col gap-2">
          <div className="flex justify-between text-xs">
            <span>{t('ptz_pan')}</span>
            <span className="font-mono">{pan}°</span>
          </div>
          <input
            type="range"
            min="0"
            max="360"
            value={pan}
            onChange={(e) => onMove(Number(e.target.value), tilt, zoom)}
            className="w-full accent-primary"
          />
        </div>

        <div className="flex flex-col gap-2">
          <div className="flex justify-between text-xs">
            <span>{t('ptz_tilt')}</span>
            <span className="font-mono">{tilt}°</span>
          </div>
          <input
            type="range"
            min="-90"
            max="90"
            value={tilt}
            onChange={(e) => onMove(pan, Number(e.target.value), zoom)}
            className="w-full accent-primary"
          />
        </div>

        <div className="flex flex-col gap-2">
          <div className="flex justify-between text-xs">
            <span>{t('ptz_zoom')}</span>
            <span className="font-mono">{zoom}x</span>
          </div>
          <input
            type="range"
            min="1"
            max="10"
            value={zoom}
            onChange={(e) => onMove(pan, tilt, Number(e.target.value))}
            className="w-full accent-primary"
          />
        </div>

        <div className="grid grid-cols-3 gap-2 p-4 bg-surface-container rounded-xl w-48 mx-auto">
          <div />
          <Btn tone="slate" onClick={() => onMove(pan, Math.min(90, tilt + 15), zoom)}>▲</Btn>
          <div />
          <Btn tone="slate" onClick={() => onMove((pan - 15 + 360) % 360, tilt, zoom)}>◀</Btn>
          <Btn tone="cyan" onClick={() => onMove(180, 0, 1)}>
            <Compass className="h-3.5 w-3.5" />
          </Btn>
          <Btn tone="slate" onClick={() => onMove((pan + 15) % 360, tilt, zoom)}>▶</Btn>
          <div />
          <Btn tone="slate" onClick={() => onMove(pan, Math.max(-90, tilt - 15), zoom)}>▼</Btn>
          <div />
        </div>
      </div>
    </Panel>
  );
};
