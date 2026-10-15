import React, { useEffect, useState } from 'react';
import { Camera, Loader2, VideoOff } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { CameraSource, liveUrl, takePhoto } from '../data/camerasApi';
import { useCameraI18n } from '../scope';

const STILL_REFRESH_MS = 2000;

interface LivePreviewProps {
  readonly source: CameraSource;
  readonly onPhoto: () => void;
}

export const LivePreview: React.FC<LivePreviewProps> = ({ source, onPhoto }) => {
  const { t } = useCameraI18n();
  const [failed, setFailed] = useState(false);
  const [stamp, setStamp] = useState(0);
  const [shooting, setShooting] = useState(false);

  useEffect(() => {
    setFailed(false);
    if (source.stream) {
      return;
    }
    const timer = window.setInterval(() => setStamp(Date.now()), STILL_REFRESH_MS);
    return () => window.clearInterval(timer);
  }, [source.id, source.stream]);

  const transform = source.clientTransform
    ? `rotate(${source.options.rotate}deg)${source.options.mirror ? ' scaleX(-1)' : ''}`
    : undefined;
  const src = source.stream ? liveUrl(source.id, true) : `${liveUrl(source.id, false)}?t=${stamp}`;

  const shoot = async () => {
    setShooting(true);
    try {
      await takePhoto(source.id);
      onPhoto();
    } catch (cause) {
      reportError('node_camera_photo_failed', cause);
    } finally {
      setShooting(false);
    }
  };

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-800/80 bg-black">
      <div className="relative aspect-video max-h-[60vh] w-full bg-slate-950">
        {failed ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-sm text-slate-400">
            <VideoOff className="h-8 w-8 text-rose-300" aria-hidden="true" />
            {t('live_failed')}
          </div>
        ) : (
          <img
            key={source.id}
            src={src}
            alt={t('live_alt', { name: source.name })}
            onError={() => setFailed(true)}
            className="absolute inset-0 h-full w-full object-contain"
            style={{ transform }}
          />
        )}
        <span className="absolute left-3 top-3 flex items-center gap-1.5 rounded-full bg-black/60 px-2.5 py-1 text-[11px] font-semibold text-white backdrop-blur">
          <span className={`h-2 w-2 rounded-full ${failed ? 'bg-slate-500' : 'animate-pulse bg-rose-500'}`} aria-hidden="true" />
          {t(source.stream ? 'live_badge' : 'still_badge')}
        </span>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-800/80 bg-slate-950/80 px-3 py-2">
        <p className="min-w-0 truncate text-sm font-semibold text-slate-100">{source.name}</p>
        <button
          type="button"
          onClick={shoot}
          disabled={shooting || failed}
          className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-400 to-indigo-500 px-3 py-1.5 text-xs font-bold text-slate-950 transition hover:brightness-110 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-200"
        >
          {shooting ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : <Camera className="h-3.5 w-3.5" aria-hidden="true" />}
          {t('photo_take')}
        </button>
      </div>
    </div>
  );
};
