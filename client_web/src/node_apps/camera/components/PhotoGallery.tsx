import React, { useEffect, useState } from 'react';
import { Trash2 } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { Panel } from '../../shared/components/ModuleFrame';
import { CameraPhoto, deletePhoto, fetchPhotos, photoUrl } from '../data/camerasApi';
import { useCameraI18n } from '../scope';

interface PhotoGalleryProps {
  readonly sourceId: string;
  readonly refreshKey: number;
}

export const PhotoGallery: React.FC<PhotoGalleryProps> = ({ sourceId, refreshKey }) => {
  const { t, lang } = useCameraI18n();
  const [photos, setPhotos] = useState<readonly CameraPhoto[]>([]);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    fetchPhotos(sourceId, controller.signal)
      .then(setPhotos)
      .catch((cause: unknown) => !controller.signal.aborted && reportError('node_camera_photos_failed', cause));
    return () => controller.abort();
  }, [sourceId, refreshKey, tick]);

  const remove = async (name: string) => {
    try {
      await deletePhoto(sourceId, name);
      setTick((value) => value + 1);
    } catch (cause) {
      reportError('node_camera_photos_failed', cause);
    }
  };

  const format = new Intl.DateTimeFormat(lang, { dateStyle: 'short', timeStyle: 'short' });
  return (
    <Panel title={t('photos_title', { count: photos.length })}>
      {photos.length === 0 ? (
        <p className="text-sm text-slate-500">{t('photos_empty')}</p>
      ) : (
        <ul className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-4">
          {photos.map((photo) => (
            <li key={photo.name} className="group relative overflow-hidden rounded-xl border border-slate-800/80 bg-black">
              <a href={photoUrl(sourceId, photo.name)} target="_blank" rel="noopener noreferrer">
                <img src={photoUrl(sourceId, photo.name)} alt={t('photo_alt', { when: format.format(photo.at * 1000) })} loading="lazy" className="aspect-video w-full object-cover" />
              </a>
              <div className="flex items-center justify-between gap-1 bg-slate-950/90 px-2 py-1">
                <time className="truncate font-mono text-[10px] text-slate-400">{format.format(photo.at * 1000)}</time>
                <button
                  type="button"
                  onClick={() => void remove(photo.name)}
                  aria-label={t('photo_delete')}
                  className="rounded p-1 text-slate-500 transition hover:text-rose-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-300"
                >
                  <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
};
