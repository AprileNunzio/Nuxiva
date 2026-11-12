import React from 'react';
import { ScanFace } from 'lucide-react';
import { CameraVitals } from '../data/healthApi';
import { chipClass, usePeopleI18n } from '../scope';

interface Props {
  readonly camera: CameraVitals;
  readonly busy: string | null;
  readonly onToggle: () => void;
}

const TONE: Record<CameraVitals['state'], string> = {
  off: 'border-slate-300 text-slate-600',
  band: 'border-slate-300 text-slate-600',
  busy: 'border-amber-300 text-amber-800',
  idle: 'border-teal-300 text-teal-800',
  measuring: 'border-teal-400 text-teal-900',
  streaming: 'border-emerald-400 text-emerald-800',
};

export const WebcamSource: React.FC<Props> = ({ camera, busy, onToggle }) => {
  const { t } = usePeopleI18n();
  const pct = Math.round(camera.progress * 100);
  return (
    <article className="flex flex-col gap-2 rounded-xl border border-teal-200 bg-gradient-to-br from-teal-50 to-white p-4">
      <header className="flex flex-wrap items-center gap-2">
        <ScanFace className={`h-4 w-4 text-teal-700 ${camera.state === 'measuring' || camera.state === 'streaming' ? 'animate-pulse' : ''}`} aria-hidden="true" />
        <h4 className="font-semibold text-slate-900">{t('hl_cam_title')}</h4>
        <span role="status" className={`ml-auto rounded-full border px-2 py-0.5 text-xs ${TONE[camera.state]}`}>
          {t(`hl_cam_${camera.state}`, { pct })}
        </span>
      </header>
      {camera.state === 'measuring' && (
        <div className="h-1.5 overflow-hidden rounded-full bg-teal-100" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct} aria-label={t('hl_cam_measuring', { pct })}>
          <div className="h-full rounded-full bg-teal-500 transition-[width] duration-700" style={{ width: `${pct}%` }} />
        </div>
      )}
      <p className="text-xs text-slate-600">{t('hl_cam_hint')}</p>
      <p className="text-xs text-slate-600">{t('hl_cam_private')}</p>
      <p className="text-[11px] text-slate-500">{t('hl_cam_tips')}</p>
      <p className="text-[11px] text-slate-500">{t('hl_cam_cost')}</p>
      <div className="mt-auto">
        <button type="button" disabled={busy !== null} aria-pressed={camera.enabled} onClick={onToggle}
          className={`${chipClass} ${camera.enabled ? 'border-teal-300 bg-white text-teal-900' : 'border-teal-600 bg-teal-600 text-white'}`}>
          {t(camera.enabled ? 'hl_cam_disable' : 'hl_cam_enable')}
        </button>
      </div>
    </article>
  );
};
