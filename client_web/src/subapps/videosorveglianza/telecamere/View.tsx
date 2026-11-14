import React, { useState, useEffect, useCallback, FormEvent } from 'react';
import { Video, Plus, Trash2, Radio, RefreshCw, Shield, Camera, Check, X } from 'lucide-react';
import { useScopedI18n } from '../../../shared/i18n/useScopedI18n';
import { fetchCameras, fetchSources, addCamera, patchCamera, deleteCamera } from './api';
import { Snapshot } from './components/Snapshot';
import type { CameraRow, CameraSource } from './types';

export function View() {
  const { t } = useScopedI18n('subapps/videosorveglianza/telecamere');
  const [cameras, setCameras] = useState<CameraRow[]>([]);
  const [sources, setSources] = useState<CameraSource[]>([]);
  const [kinds, setKinds] = useState<string[]>(['webcam', 'rtsp', 'rtsps', 'onvif', 'hikvision']);
  const [retentions, setRetentions] = useState<number[]>([5, 15, 60]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const [name, setName] = useState('');
  const [kind, setKind] = useState('rtsp');
  const [url, setUrl] = useState('');
  const [retention, setRetention] = useState(5);

  const loadData = useCallback(async () => {
    const [camerasData, sourcesData] = await Promise.all([
      fetchCameras(),
      fetchSources(),
    ]);
    setCameras([...camerasData.cameras]);
    if (camerasData.kinds.length > 0) setKinds([...camerasData.kinds]);
    if (camerasData.retentions.length > 0) setRetentions([...camerasData.retentions]);
    setSources([...sourcesData]);
    setLoading(false);
    setRefreshing(false);
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleRefresh = () => {
    setRefreshing(true);
    loadData();
  };

  const handleAddSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    if (kind !== 'webcam' && !url.trim()) return;

    setSubmitting(true);
    const created = await addCamera({
      name: name.trim(),
      kind,
      url: url.trim(),
      retention_min: retention,
    });

    if (created) {
      setName('');
      setUrl('');
      setShowAdd(false);
      await loadData();
    }
    setSubmitting(false);
  };

  const handleToggle = async (id: string, field: 'enabled' | 'record' | 'consent', currentValue: boolean) => {
    const updated = await patchCamera(id, { [field]: !currentValue });
    if (updated) {
      setCameras((prev) =>
        prev.map((cam) => (cam.id === id ? { ...cam, ...updated } : cam))
      );
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm(t('delete_confirm'))) {
      return;
    }
    const success = await deleteCamera(id);
    if (success) {
      setCameras((prev) => prev.filter((c) => c.id !== id));
      setSources((prev) => prev.filter((s) => s.id !== `c-${id}`));
    }
  };

  const activeCount = cameras.filter((c) => c.enabled).length;
  const recordingCount = cameras.filter((c) => c.recording).length;
  const needsUrl = kind !== 'webcam';

  const liveFeeds = React.useMemo(() => {
    const seenIds = new Set<string>();
    const feeds: Array<{ id: string; name: string; isRecording: boolean }> = [];

    for (const source of sources) {
      seenIds.add(source.id);
      const matchedCam = cameras.find((c) => `c-${c.id}` === source.id);
      feeds.push({
        id: source.id,
        name: source.name,
        isRecording: Boolean(matchedCam?.recording),
      });
    }

    for (const cam of cameras) {
      const sourceId = `c-${cam.id}`;
      if (!seenIds.has(sourceId)) {
        seenIds.add(sourceId);
        feeds.push({
          id: sourceId,
          name: cam.name,
          isRecording: Boolean(cam.recording),
        });
      }
    }

    return feeds;
  }, [sources, cameras]);

  return (
    <div className="flex h-full flex-col overflow-y-auto bg-surface p-4 sm:p-6 text-on-surface">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-4 border-b border-outline-variant/40 pb-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-primary/10 text-primary">
            <Video className="h-6 w-6 stroke-[1.8]" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-on-surface">{t('title')}</h1>
            <p className="text-xs text-on-surface-variant">{t('subtitle')}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-1.5 rounded-xl border border-outline-variant bg-surface-container px-3 py-2 text-xs font-semibold text-on-surface hover:bg-surface-container-high transition-colors"
            title={t('refresh')}
          >
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">{t('refresh')}</span>
          </button>

          <button
            type="button"
            onClick={() => setShowAdd((v) => !v)}
            className="flex items-center gap-1.5 rounded-xl bg-primary px-4 py-2 text-xs font-bold text-on-primary shadow-sm hover:opacity-90 active:scale-[0.98] transition-all"
          >
            <Plus className="h-4 w-4" />
            <span>{t('add')}</span>
          </button>
        </div>
      </header>

      <section className="mb-6 os-tiles [--tile-min:9rem] [--tile-gap:0.75rem]">
        <div className="flex items-center gap-3 rounded-2xl border border-outline-variant/50 bg-surface-container p-3.5 shadow-sm">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-surface-container-high text-primary">
            <Camera className="h-5 w-5" />
          </div>
          <div>
            <div className="text-[11px] font-medium text-on-surface-variant">{t('stat_total')}</div>
            <div className="text-lg font-bold text-on-surface">{cameras.length}</div>
          </div>
        </div>

        <div className="flex items-center gap-3 rounded-2xl border border-outline-variant/50 bg-surface-container p-3.5 shadow-sm">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-500">
            <Radio className="h-5 w-5" />
          </div>
          <div>
            <div className="text-[11px] font-medium text-on-surface-variant">{t('stat_active')}</div>
            <div className="text-lg font-bold text-emerald-600 dark:text-emerald-400">{activeCount}</div>
          </div>
        </div>

        <div className="flex items-center gap-3 rounded-2xl border border-outline-variant/50 bg-surface-container p-3.5 shadow-sm">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-error/10 text-error">
            <Shield className="h-5 w-5" />
          </div>
          <div>
            <div className="text-[11px] font-medium text-on-surface-variant">{t('stat_recording')}</div>
            <div className="text-lg font-bold text-error">{recordingCount}</div>
          </div>
        </div>
      </section>

      {showAdd && (
        <section className="mb-6 rounded-2xl border border-primary/30 bg-surface-container p-5 shadow-md">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-bold text-on-surface">{t('add_title')}</h2>
            <button
              type="button"
              onClick={() => setShowAdd(false)}
              className="rounded-lg p-1 text-on-surface-variant hover:bg-surface-container-high"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <form onSubmit={handleAddSubmit} className="flex flex-col gap-4">
            <div className="os-tiles [--tile-min:14rem]">
              <div>
                <label className="mb-1 block text-xs font-semibold text-on-surface-variant">
                  {t('field_name')}
                </label>
                <input
                  type="text"
                  maxLength={60}
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Front Porch RTSP"
                  className="w-full rounded-xl border border-outline-variant bg-surface-container-high px-3 py-2 text-xs text-on-surface outline-none focus:border-primary"
                />
              </div>

              <div>
                <label className="mb-1 block text-xs font-semibold text-on-surface-variant">
                  {t('field_kind')}
                </label>
                <select
                  value={kind}
                  onChange={(e) => setKind(e.target.value)}
                  className="w-full rounded-xl border border-outline-variant bg-surface-container-high px-3 py-2 text-xs text-on-surface outline-none focus:border-primary"
                >
                  {kinds.map((k) => (
                    <option key={k} value={k}>
                      {k.toUpperCase()}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-1 block text-xs font-semibold text-on-surface-variant">
                  {needsUrl ? t('field_url') : t('field_device')}
                </label>
                <input
                  type="text"
                  required={needsUrl}
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder={needsUrl ? (kind === 'rtsps' ? `rtsps:${String.fromCharCode(47, 47)}` : `rtsp:${String.fromCharCode(47, 47)}`) : '0'}
                  className="w-full rounded-xl border border-outline-variant bg-surface-container-high px-3 py-2 text-xs text-on-surface outline-none focus:border-primary"
                />
              </div>

              <div>
                <label className="mb-1 block text-xs font-semibold text-on-surface-variant">
                  {t('field_retention')}
                </label>
                <select
                  value={retention}
                  onChange={(e) => setRetention(Number(e.target.value))}
                  className="w-full rounded-xl border border-outline-variant bg-surface-container-high px-3 py-2 text-xs text-on-surface outline-none focus:border-primary"
                >
                  {retentions.map((m) => (
                    <option key={m} value={m}>
                      {t('minutes', { n: m })}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <p className="text-[11px] text-on-surface-variant">{t('consent_note')}</p>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowAdd(false)}
                className="rounded-xl border border-outline-variant px-4 py-2 text-xs font-semibold text-on-surface hover:bg-surface-container-high"
              >
                {t('cancel')}
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="flex items-center gap-1.5 rounded-xl bg-primary px-4 py-2 text-xs font-bold text-on-primary shadow-sm hover:opacity-90 disabled:opacity-50"
              >
                <Check className="h-3.5 w-3.5" />
                <span>{t('save')}</span>
              </button>
            </div>
          </form>
        </section>
      )}

      <section className="mb-8 flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <Radio className="h-4 w-4 text-emerald-500" />
          <h2 className="text-sm font-bold tracking-tight text-on-surface">{t('live_title')}</h2>
        </div>

        {liveFeeds.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-2 rounded-2xl border border-dashed border-outline-variant/60 py-10 text-center text-outline">
            <Video className="h-10 w-10 stroke-[1.2]" />
            <p className="text-xs">{t('empty_sources')}</p>
          </div>
        ) : (
          <div className="os-tiles [--tile-min:16rem]">
            {liveFeeds.map((feed) => (
              <Snapshot
                key={feed.id}
                sourceId={feed.id}
                name={feed.name}
                offlineLabel={t('offline')}
                liveLabel={t('live_label')}
                isRecording={feed.isRecording}
              />
            ))}
          </div>
        )}
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-sm font-bold tracking-tight text-on-surface">{t('title')}</h2>

        {cameras.length === 0 && !loading ? (
          <div className="flex flex-col items-center justify-center gap-2 rounded-2xl border border-outline-variant/40 bg-surface-container py-8 text-center text-outline">
            <Camera className="h-8 w-8 stroke-[1.5]" />
            <p className="text-xs">{t('empty')}</p>
          </div>
        ) : (
          <div className="flex flex-col gap-2.5">
            {cameras.map((camera) => (
              <div
                key={camera.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-outline-variant/60 bg-surface-container px-4 py-3 shadow-sm hover:border-outline-variant"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-surface-container-high text-primary">
                    <Camera className="h-4 w-4" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-on-surface">{camera.name}</span>
                      <span className="rounded-md bg-surface-container-high px-1.5 py-0.5 text-[10px] font-mono uppercase text-on-surface-variant">
                        {camera.kind}
                      </span>
                      {camera.recording && (
                        <span className="rounded-md bg-error/10 px-1.5 py-0.5 text-[10px] font-bold text-error">
                          REC
                        </span>
                      )}
                    </div>
                    <span className="text-[10px] text-outline font-mono">{camera.id}</span>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-4">
                  <label className="flex items-center gap-1.5 text-xs text-on-surface-variant cursor-pointer">
                    <input
                      type="checkbox"
                      checked={camera.enabled}
                      onChange={() => handleToggle(camera.id, 'enabled', camera.enabled)}
                      className="rounded accent-primary"
                    />
                    <span>{t('enabled')}</span>
                  </label>

                  <label className="flex items-center gap-1.5 text-xs text-on-surface-variant cursor-pointer">
                    <input
                      type="checkbox"
                      checked={Boolean(camera.record)}
                      onChange={() => handleToggle(camera.id, 'record', Boolean(camera.record))}
                      className="rounded accent-primary"
                    />
                    <span>{t('record')}</span>
                  </label>

                  <label className="flex items-center gap-1.5 text-xs text-on-surface-variant cursor-pointer">
                    <input
                      type="checkbox"
                      checked={Boolean(camera.consent)}
                      onChange={() => handleToggle(camera.id, 'consent', Boolean(camera.consent))}
                      className="rounded accent-primary"
                    />
                    <span>{t('consent')}</span>
                  </label>

                  <button
                    type="button"
                    onClick={() => handleDelete(camera.id)}
                    className="rounded-lg p-1.5 text-outline hover:bg-error/10 hover:text-error transition-colors"
                    title={t('delete')}
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

export default View;
