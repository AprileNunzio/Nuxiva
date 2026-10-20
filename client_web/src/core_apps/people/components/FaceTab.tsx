import React, { useEffect, useRef, useState } from 'react';
import { Camera, Loader2, RefreshCw, Trash2, Upload } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { PHOTO_KINDS, Photo, PhotoKind, capturePhoto, deletePhoto, fetchCoverage, fetchPhotos, reproject, uploadPhoto } from '../data/peopleApi';
import { chipClass, usePeopleI18n } from '../scope';

interface FaceTabProps {
  readonly slug: string;
  readonly quality: number;
  readonly busy: string | null;
  readonly run: (key: string, task: () => Promise<unknown>, code: string) => Promise<boolean>;
}

export const FaceTab: React.FC<FaceTabProps> = ({ slug, quality, busy, run }) => {
  const { t } = usePeopleI18n();
  const [photos, setPhotos] = useState<readonly Photo[]>([]);
  const [coverage, setCoverage] = useState<Record<string, number>>({});
  const [tick, setTick] = useState(0);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([fetchPhotos(slug, controller.signal), fetchCoverage(slug, controller.signal)])
      .then(([p, c]) => {
        setPhotos(p);
        setCoverage(c);
      })
      .catch((cause: unknown) => !controller.signal.aborted && reportError('people_photos_failed', cause));
    return () => controller.abort();
  }, [slug, tick]);

  const act = async (key: string, task: () => Promise<unknown>, code: string) => {
    if (await run(key, task, code)) {
      setTick((v) => v + 1);
    }
  };
  const done = PHOTO_KINDS.filter((k) => (coverage[k] ?? 0) > 0).length;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex-1">
          <p className="text-sm text-slate-200">{t('face_coverage', { done, total: PHOTO_KINDS.length })}</p>
          <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-slate-800">
            <div className="h-full rounded-full bg-gradient-to-r from-cyan-400 to-emerald-400" style={{ width: `${(done / PHOTO_KINDS.length) * 100}%` }} />
          </div>
          <p className="mt-1 text-[11px] text-slate-500">{t('face_quality', { quality: Math.round(quality) })}</p>
        </div>
        <button type="button" disabled={busy !== null} onClick={() => void act('reproject', () => reproject(slug), 'people_reproject_failed')} className={`${chipClass} border-slate-700 py-2 text-slate-200`}>
          {busy === 'reproject' ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />}
          {t('recalibrate')}
        </button>
        <button type="button" disabled={busy !== null} onClick={() => input.current?.click()} className={`${chipClass} border-cyan-400/50 bg-cyan-400/10 py-2 text-cyan-100`}>
          <Upload className="h-3.5 w-3.5" aria-hidden="true" />
          {t('upload_photo')}
        </button>
        <input
          ref={input}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          hidden
          onChange={(event) => {
            const file = event.target.files?.[0];
            event.target.value = '';
            if (file && file.size <= 8 * 1024 * 1024) {
              void act('upload', () => uploadPhoto(slug, file), 'people_upload_failed');
            } else if (file) {
              reportError('people_upload_failed', new Error('too_large'));
            }
          }}
        />
      </div>
      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">{t('scan_title')}</p>
        <p className="mb-3 text-xs text-slate-500">{t('scan_hint')}</p>
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-5 xl:grid-cols-9">
          {PHOTO_KINDS.map((kind: PhotoKind) => {
            const count = coverage[kind] ?? 0;
            return (
              <button
                key={kind}
                type="button"
                disabled={busy !== null}
                onClick={() => void act(`capture:${kind}`, () => capturePhoto(slug, kind), 'people_capture_failed')}
                className={`flex flex-col items-center gap-1 rounded-xl border p-2 text-center text-[11px] transition disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${
                  count ? 'border-emerald-400/50 bg-emerald-400/10 text-emerald-100' : 'border-slate-700 bg-slate-950/40 text-slate-300 hover:border-cyan-400/50'
                }`}
              >
                {busy === `capture:${kind}` ? <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" /> : <Camera className="h-5 w-5" aria-hidden="true" />}
                {t(`view_${kind}`)}
                <span className="font-mono text-[10px] opacity-70">{count}</span>
              </button>
            );
          })}
        </div>
      </div>
      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">{t('gallery', { count: photos.length })}</p>
        {photos.length === 0 ? (
          <p className="text-sm text-slate-500">{t('gallery_empty')}</p>
        ) : (
          <ul className="grid grid-cols-3 gap-2 sm:grid-cols-4 xl:grid-cols-6 3xl:grid-cols-8 5xl:grid-cols-12">
            {photos.map((photo) => (
              <li key={photo.id} className="group relative overflow-hidden rounded-xl border border-slate-800/80 bg-slate-950">
                <img src={photo.url} alt={t(`view_${photo.kind}`)} loading="lazy" className="aspect-square w-full object-cover" />
                <span className="absolute left-1 top-1 rounded bg-black/60 px-1.5 py-0.5 text-[10px] text-white">{photo.primary ? t('primary') : t(`view_${photo.kind}`)}</span>
                <button
                  type="button"
                  disabled={busy !== null}
                  aria-label={t('delete_photo')}
                  onClick={() => void act(`photo:${photo.id}`, () => deletePhoto(slug, photo.id), 'people_photo_delete_failed')}
                  className="absolute right-1 top-1 flex min-h-10 min-w-10 items-center justify-center rounded-lg bg-black/75 p-2 text-slate-200 transition hover:text-rose-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-300"
                >
                  <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};
