import React, { useEffect, useRef, useState } from 'react';
import { Camera, Loader2, MonitorSmartphone } from 'lucide-react';
import { PHOTO_KINDS, PhotoKind, uploadPhoto } from '../data/peopleApi';
import { DeviceAccess } from '../devices/DeviceAccess';
import { useMediaAccess } from '../devices/useMediaAccess';
import { chipClass, primaryClass, usePeopleI18n } from '../scope';

interface Props {
  readonly slug: string;
  readonly busy: string | null;
  readonly coverage: Readonly<Record<string, number>>;
  readonly act: (key: string, task: () => Promise<unknown>, code: string) => Promise<void>;
}

const JPEG_QUALITY = 0.9;

function grab(video: HTMLVideoElement): Promise<Blob> {
  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const context = canvas.getContext('2d');
  if (!context || !canvas.width || !canvas.height) {
    return Promise.reject(new Error('no_frame'));
  }
  context.drawImage(video, 0, 0, canvas.width, canvas.height);
  return new Promise((resolve, reject) => canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error('no_frame'))), 'image/jpeg', JPEG_QUALITY));
}

export const PcCamera: React.FC<Props> = ({ slug, busy, coverage, act }) => {
  const { t } = usePeopleI18n();
  const access = useMediaAccess('camera');
  const video = useRef<HTMLVideoElement>(null);
  const [kind, setKind] = useState<PhotoKind>(() => PHOTO_KINDS.find((k) => !(coverage[k] ?? 0)) ?? 'front');

  useEffect(() => {
    if (video.current) {
      video.current.srcObject = access.stream;
    }
  }, [access.stream]);

  const shoot = () => {
    const element = video.current;
    if (!element) {
      return;
    }
    void act(`pc:${kind}`, async () => {
      await uploadPhoto(slug, await grab(element), kind);
      const next = PHOTO_KINDS.find((k) => k !== kind && !(coverage[k] ?? 0));
      if (next) {
        setKind(next);
      }
    }, 'people_capture_failed');
  };

  return (
    <section aria-labelledby="pc-camera-title" className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-3 sm:p-4">
      <header className="flex items-center gap-2">
        <MonitorSmartphone className="h-4 w-4 text-blue-700" aria-hidden="true" />
        <h3 id="pc-camera-title" className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-600">{t('pc_cam_title')}</h3>
      </header>
      <p className="text-xs text-slate-500">{t('pc_cam_hint')}</p>
      <DeviceAccess kind="camera" state={access.state} devices={access.devices} deviceId={access.deviceId} active={access.stream !== null}
        onRequest={(id) => void access.request(id)} onRelease={access.release} />
      {access.stream && (
        <div className="grid gap-3 cq-lg:grid-cols-[minmax(0,1fr)_16rem]">
          <div className="relative overflow-hidden rounded-xl bg-black">
            <video ref={video} autoPlay playsInline muted className="aspect-video max-h-[26rem] w-full -scale-x-100 object-cover" aria-label={t('pc_cam_preview')} />
            <span className="pointer-events-none absolute inset-x-0 bottom-2 mx-auto w-fit rounded-full bg-black/60 px-3 py-1 text-xs text-white">{t(`view_${kind}`)}</span>
          </div>
          <div className="flex flex-col gap-2">
            <p className="text-xs font-semibold text-slate-700">{t('pc_cam_pose')}</p>
            <div className="grid grid-cols-3 gap-1.5" role="radiogroup" aria-label={t('pc_cam_pose')}>
              {PHOTO_KINDS.map((k) => (
                <button key={k} type="button" role="radio" aria-checked={kind === k} onClick={() => setKind(k)}
                  className={`${chipClass} justify-center py-1.5 text-[11px] ${kind === k ? 'border-blue-300 bg-blue-50 text-blue-900' : (coverage[k] ?? 0) ? 'border-emerald-300 text-emerald-800' : 'border-slate-300 text-slate-700'}`}>
                  {t(`view_${k}`)}
                </button>
              ))}
            </div>
            <button type="button" disabled={busy !== null} onClick={shoot} className={`${primaryClass} mt-auto`}>
              {busy === `pc:${kind}` ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Camera className="h-4 w-4" aria-hidden="true" />}
              {t('pc_cam_shoot', { view: t(`view_${kind}`) })}
            </button>
          </div>
        </div>
      )}
    </section>
  );
};
