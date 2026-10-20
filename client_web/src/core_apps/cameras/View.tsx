import React, { FormEvent, useState } from 'react';
import { Plus, Trash2, Video } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { AppFrame, Btn, Empty, Field, List, Loading, Panel, Pill, Row, Stat, StatRow, Toggle, Unreachable, inputClass } from '../shared/kit';
import { asList } from '../shared/http';
import { useAction, useResource } from '../shared/useResource';
import { addCamera, deleteCamera, patchCamera } from './api';
import { Snapshot } from './components/Snapshot';
import { CameraSource, CamerasOverview } from './types';

export const View: React.FC = () => {
  const { t } = useScopedI18n('core_apps/cameras');
  const { data, error, loading, reload } = useResource<CamerasOverview>('/api/cameras', 20000);
  const sources = useResource<{ sources: CameraSource[] }>('/api/cameras/sources', 20000);
  const { busy, run } = useAction(() => {
    reload();
    sources.reload();
  });
  const [name, setName] = useState('');
  const [kind, setKind] = useState('webcam');
  const [url, setUrl] = useState('');
  const [retention, setRetention] = useState(5);

  if (loading && !data) {
    return <Loading label={t('loading')} />;
  }
  if (!data) {
    return <Unreachable label={t(error ? 'unreachable' : 'loading')} />;
  }

  const live = asList<CameraSource>(sources.data?.sources);
  const recording = data.cameras.filter((camera) => camera.recording).length;
  const needsUrl = kind !== 'webcam';

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!name.trim() || (needsUrl && !url.trim())) {
      return;
    }
    const done = await run(() => addCamera({ name: name.trim(), kind, url: url.trim(), retention_min: retention }), 'cameras_add_failed');
    if (done !== null) {
      setName('');
      setUrl('');
    }
  };

  return (
    <AppFrame title={t('title')} description={t('description')} onReload={reload}>
      <StatRow>
        <Stat label={t('stat_total')} value={data.cameras.length} />
        <Stat label={t('stat_active')} value={data.cameras.filter((camera) => camera.enabled).length} tone="emerald" />
        <Stat label={t('stat_recording')} value={recording} tone="rose" />
      </StatRow>
      {live.length > 0 ? (
        <Panel title={t('live_title')} icon={<Video className="h-4 w-4 text-rose-300" aria-hidden="true" />}>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 3xl:grid-cols-4">
            {live.map((source) => (
              <Snapshot key={source.id} sourceId={source.id} name={source.name} offline={t('offline')} />
            ))}
          </div>
        </Panel>
      ) : null}
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
        <Panel title={t('list_title')}>
          {data.cameras.length === 0 ? (
            <Empty>{t('list_empty')}</Empty>
          ) : (
            <List>
              {data.cameras.map((camera) => (
                <Row
                  key={camera.id}
                  actions={
                    <Btn tone="rose" busy={busy} onClick={() => void run(() => deleteCamera(camera.id), 'cameras_delete_failed')} title={t('delete')}>
                      <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                    </Btn>
                  }
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <b>{camera.name}</b>
                    <Pill>{camera.kind}</Pill>
                    {camera.recording ? <Pill tone="rose">{t('recording')}</Pill> : null}
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-slate-400">
                    <label className="flex items-center gap-2">
                      <Toggle checked={camera.enabled} disabled={busy} label={t('enabled')} onChange={(value) => void run(() => patchCamera(camera.id, { enabled: value }), 'cameras_patch_failed')} />
                      {t('enabled')}
                    </label>
                    <label className="flex items-center gap-2">
                      <Toggle checked={camera.record} disabled={busy} label={t('record')} onChange={(value) => void run(() => patchCamera(camera.id, { record: value }), 'cameras_patch_failed')} />
                      {t('record')}
                    </label>
                    <label className="flex items-center gap-2">
                      <Toggle checked={camera.consent} disabled={busy} label={t('consent')} onChange={(value) => void run(() => patchCamera(camera.id, { consent: value }), 'cameras_patch_failed')} />
                      {t('consent')}
                    </label>
                  </div>
                </Row>
              ))}
            </List>
          )}
        </Panel>
        <Panel title={t('add_title')} icon={<Plus className="h-4 w-4 text-cyan-300" aria-hidden="true" />}>
          <form onSubmit={submit} className="flex flex-col gap-3">
            <Field label={t('field_name')}>
              <input className={inputClass} value={name} maxLength={60} onChange={(event) => setName(event.target.value)} required />
            </Field>
            <Field label={t('field_kind')}>
              <select className={inputClass} value={kind} onChange={(event) => setKind(event.target.value)}>
                {data.kinds.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </Field>
            <Field label={needsUrl ? t('field_url') : t('field_device')}>
              <input className={inputClass} value={url} onChange={(event) => setUrl(event.target.value)} placeholder={needsUrl ? (kind === 'rtsps' ? 'rtsps://…' : 'rtsp://…') : '0'} required={needsUrl} />
            </Field>
            <Field label={t('field_retention')}>
              <select className={inputClass} value={retention} onChange={(event) => setRetention(Number(event.target.value))}>
                {data.retentions.map((item) => (
                  <option key={item} value={item}>
                    {t('minutes', { n: item })}
                  </option>
                ))}
              </select>
            </Field>
            <Btn type="submit" busy={busy}>
              {t('add')}
            </Btn>
            <p className="text-xs text-slate-500">{t('consent_note')}</p>
          </form>
        </Panel>
      </div>
    </AppFrame>
  );
};

export default View;
