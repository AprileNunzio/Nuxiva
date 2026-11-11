import React, { useState, useEffect, useCallback, FormEvent } from 'react';
import { Video, Plus, Trash2, Radio } from 'lucide-react';
import { useScopedI18n } from '../../../shared/i18n/useScopedI18n';

interface CameraItem {
  id: string;
  name: string;
  url: string;
  enabled: boolean;
  recording: boolean;
}

export function View() {
  const { t } = useScopedI18n('subapps/videosorveglianza/telecamere');
  const [cameras, setCameras] = useState<CameraItem[]>([]);
  const [name, setName] = useState('');
  const [url, setUrl] = useState('');
  const [showAdd, setShowAdd] = useState(false);

  const fetchCameras = useCallback(async () => {
    try {
      const res = await fetch('/api/cameras');
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data.cameras)) {
          setCameras(data.cameras);
        }
      }
    } catch {
      setCameras([]);
    }
  }, []);

  useEffect(() => {
    fetchCameras();
  }, [fetchCameras]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    const newCam: CameraItem = {
      id: `cam_${Date.now()}`,
      name: name.trim(),
      url: url.trim() || 'rtsp://127.0.0.1:8554/live',
      enabled: true,
      recording: false,
    };
    setCameras((prev) => [...prev, newCam]);
    setName('');
    setUrl('');
    setShowAdd(false);
  };

  const removeCam = (id: string) => {
    setCameras((prev) => prev.filter((c) => c.id !== id));
  };

  return (
    <div className="flex h-full flex-col overflow-y-auto bg-surface p-5 text-on-surface">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-outline-variant/40 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <Video className="h-5 w-5 text-primary" />
            <h1 className="text-lg font-bold tracking-tight text-on-surface">{t('title')}</h1>
          </div>
          <p className="text-xs text-on-surface-variant">{t('subtitle')}</p>
        </div>
        <button
          type="button"
          onClick={() => setShowAdd((v) => !v)}
          className="flex items-center gap-1.5 rounded-xl bg-primary px-3 py-1.5 text-xs font-bold text-on-primary shadow-sm hover:opacity-90"
        >
          <Plus className="h-3.5 w-3.5" />
          <span>{t('add')}</span>
        </button>
      </div>

      {showAdd && (
        <form onSubmit={handleSubmit} className="mb-4 flex flex-col gap-2 rounded-2xl border border-outline-variant bg-surface-container p-4">
          <input
            className="rounded-xl border border-outline-variant bg-surface-container-high px-3 py-2 text-xs text-on-surface outline-none focus:border-primary"
            placeholder={t('field_name')}
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
          <input
            className="rounded-xl border border-outline-variant bg-surface-container-high px-3 py-2 text-xs text-on-surface outline-none focus:border-primary"
            placeholder={t('field_url')}
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
          <div className="flex justify-end gap-2 pt-1">
            <button
              type="submit"
              className="rounded-xl bg-primary px-4 py-1.5 text-xs font-bold text-on-primary shadow-sm"
            >
              {t('save')}
            </button>
          </div>
        </form>
      )}

      {cameras.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 py-12 text-center text-outline">
          <Radio className="h-10 w-10 stroke-[1.5]" />
          <p className="text-xs">{t('empty')}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {cameras.map((camera) => (
            <div
              key={camera.id}
              className="flex flex-col justify-between overflow-hidden rounded-2xl border border-outline-variant/60 bg-surface-container p-3 shadow-sm"
            >
              <div className="aspect-video w-full rounded-xl bg-surface-container-highest flex items-center justify-center text-outline">
                <Video className="h-8 w-8 stroke-[1.5]" />
              </div>
              <div className="mt-3 flex items-center justify-between">
                <div>
                  <h4 className="text-xs font-bold text-on-surface">{camera.name}</h4>
                  <span className="text-[10px] text-outline">{camera.enabled ? t('status_active') : t('status_offline')}</span>
                </div>
                <button
                  type="button"
                  onClick={() => removeCam(camera.id)}
                  className="rounded-lg p-1.5 text-outline hover:bg-surface-container-highest hover:text-error"
                  title={t('delete')}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default View;
