import React, { useEffect, useState } from 'react';
import { Plus, Power, Trash2 } from 'lucide-react';
import { addLayer, listVoices, revoiceTrack } from '../api';
import { Btn, cx, Field, selectClass, Slider } from './ui';
import type { Catalog, Effect, Project, Role, Track, VoiceChoice } from '../types';
import type { Mutator, Studio } from '../useStudio';

interface Props {
  readonly studio: Studio;
  readonly project: Project;
  readonly catalog: Catalog;
  readonly track: Track | undefined;
  readonly edit: (m: Mutator) => void;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
}

const newId = () => Array.from(crypto.getRandomValues(new Uint8Array(4)), (b) => b.toString(16).padStart(2, '0')).join('');

const EffectRack: React.FC<{
  readonly effects: readonly Effect[];
  readonly catalog: Catalog;
  readonly onChange: (next: readonly Effect[]) => void;
  readonly t: Props['t'];
}> = ({ effects, catalog, onChange, t }) => {
  const [adding, setAdding] = useState('');
  const info = new Map(catalog.effects.map((e) => [e.id, e]));
  const update = (id: string, change: Partial<Effect>) => onChange(effects.map((e) => (e.id === id ? { ...e, ...change } : e)));
  return (
    <div className="space-y-2">
      {effects.map((effect) => {
        const meta = info.get(effect.type);
        return (
          <div key={effect.id} className={cx('rounded-xl border p-2.5', effect.on ? 'border-violet-200 bg-violet-50/40' : 'border-slate-200 bg-slate-50 opacity-70')}>
            <div className="mb-1.5 flex items-center gap-1.5">
              <button type="button" aria-label="toggle" onClick={() => update(effect.id, { on: !effect.on })} className={cx('rounded-md p-1', effect.on ? 'bg-violet-600 text-white' : 'bg-slate-200 text-slate-500')}>
                <Power size={11} />
              </button>
              <span className="flex-1 text-xs font-semibold text-slate-700">{meta?.name ?? effect.type}</span>
              <button type="button" aria-label={t('delete')} onClick={() => onChange(effects.filter((e) => e.id !== effect.id))} className="rounded-md p-1 text-slate-400 hover:text-rose-500">
                <Trash2 size={12} />
              </button>
            </div>
            <div className="grid grid-cols-2 gap-x-3 gap-y-1.5">
              {Object.entries(meta?.knobs ?? {}).map(([key, knob]) => (
                <label key={key} className="text-[10px] uppercase tracking-wide text-slate-500">
                  <span className="flex justify-between">
                    {key}
                    <span className="normal-case text-slate-400">{(effect.params[key] ?? knob.default).toFixed(knob.max > 100 ? 0 : 2)}{knob.unit && ` ${knob.unit}`}</span>
                  </span>
                  <Slider
                    label={key}
                    min={knob.min}
                    max={knob.max}
                    step={(knob.max - knob.min) / 200}
                    value={effect.params[key] ?? knob.default}
                    onChange={(value) => update(effect.id, { params: { ...effect.params, [key]: value } })}
                  />
                </label>
              ))}
            </div>
          </div>
        );
      })}
      <div className="flex gap-1.5">
        <select aria-label={t('add_effect')} value={adding} onChange={(e) => setAdding(e.target.value)} className={cx(selectClass, 'flex-1')}>
          <option value="">{t('add_effect')}</option>
          {catalog.effects.map((e) => (
            <option key={e.id} value={e.id}>{e.name}</option>
          ))}
        </select>
        <Btn
          tone="soft"
          disabled={!adding || effects.length >= 8}
          onClick={() => {
            const meta = info.get(adding);
            if (!meta) return;
            const params = Object.fromEntries(Object.entries(meta.knobs).map(([k, v]) => [k, v.default]));
            onChange([...effects, { id: newId(), type: adding, on: true, params }]);
            setAdding('');
          }}
        >
          <Plus size={13} />
        </Btn>
      </div>
    </div>
  );
};

export const Inspector: React.FC<Props> = ({ studio, project, catalog, track, edit, t }) => {
  const [voices, setVoices] = useState<VoiceChoice[]>([]);
  const [role, setRole] = useState<Role>('lead');
  const [busy, setBusy] = useState(false);
  const lang = track?.clips.find((c) => c.vocal)?.vocal?.lang ?? project.lyrics.lang;

  useEffect(() => {
    if (track?.role !== 'vocal') return;
    let alive = true;
    listVoices(lang).then((rows) => alive && setVoices(rows)).catch(() => alive && setVoices([]));
    return () => { alive = false; };
  }, [track?.role, lang]);

  const addTrack = async () => {
    setBusy(true);
    try {
      await studio.replace(await addLayer(project.id, role, ''));
    } catch {
      studio.setError('layer');
    } finally {
      setBusy(false);
    }
  };

  const patch = (change: Partial<Track>) => track && edit((p) => ({ ...p, tracks: p.tracks.map((tr) => (tr.id === track.id ? { ...tr, ...change } : tr)) }));

  return (
    <div className="flex flex-col gap-4 p-3">
      <section className="rounded-2xl border border-slate-200 bg-white p-3">
        <div className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">{t('add_track')}</div>
        <div className="flex gap-1.5">
          <select aria-label={t('role')} value={role} onChange={(e) => setRole(e.target.value as Role)} className={cx(selectClass, 'flex-1')}>
            {catalog.roles.filter((r) => r !== 'vocal').map((r) => (
              <option key={r} value={r}>{t(`role_${r}`)}</option>
            ))}
          </select>
          <Btn tone="accent" disabled={busy || project.job.state === 'building'} onClick={() => void addTrack()}>
            <Plus size={13} />
            {t('add')}
          </Btn>
        </div>
      </section>
      {track ? (
        <>
          <section className="space-y-3 rounded-2xl border border-slate-200 bg-white p-3">
            <div className="flex items-center gap-2">
              <span className="h-3 w-3 rounded-full" style={{ background: track.color }} />
              <input
                aria-label={t('name')}
                value={track.name}
                maxLength={40}
                onChange={(e) => patch({ name: e.target.value })}
                className="min-w-0 flex-1 rounded-md border border-transparent bg-transparent px-1 text-sm font-semibold text-slate-800 outline-none hover:border-slate-200 focus:border-violet-400"
              />
            </div>
            <Field label={t('instrument')}>
              <select value={track.instrument} disabled={track.role === 'vocal'} onChange={(e) => patch({ instrument: e.target.value })} className={selectClass}>
                {catalog.roles.map((r) => {
                  const rows = catalog.instruments.filter((i) => i.role === r);
                  return rows.length ? (
                    <optgroup key={r} label={t(`role_${r}`)}>
                      {rows.map((i) => (
                        <option key={i.id} value={i.id}>{i.name}</option>
                      ))}
                    </optgroup>
                  ) : null;
                })}
              </select>
            </Field>
            {track.role === 'vocal' && (
              <Field label={t('voice')}>
                <select
                  disabled={busy}
                  value={track.clips.find((c) => c.vocal)?.vocal?.voice ?? ''}
                  onChange={async (e) => {
                    setBusy(true);
                    try {
                      await studio.replace(await revoiceTrack(project.id, track.id, e.target.value));
                    } catch {
                      studio.setError('voice');
                    } finally {
                      setBusy(false);
                    }
                  }}
                  className={selectClass}
                >
                  <option value="">{t('voice_auto')}</option>
                  {voices.map((v) => (
                    <option key={v.id} value={v.id}>{v.name}{v.preferred ? ' ★' : ''}</option>
                  ))}
                </select>
              </Field>
            )}
            <Field label={`${t('volume')} · ${Math.round(track.volume * 100)}%`}>
              <Slider label={t('volume')} min={0} max={1.5} value={track.volume} onChange={(volume) => patch({ volume })} />
            </Field>
            <Field label={`${t('pan')} · ${track.pan.toFixed(2)}`}>
              <Slider label={t('pan')} min={-1} max={1} value={track.pan} onChange={(pan) => patch({ pan })} />
            </Field>
            <Btn
              tone="danger"
              onClick={() => edit((p) => ({ ...p, tracks: p.tracks.filter((tr) => tr.id !== track.id) }))}
            >
              <Trash2 size={13} />
              {t('delete_track')}
            </Btn>
          </section>
          <section>
            <div className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">{t('effects')}</div>
            <EffectRack effects={track.effects} catalog={catalog} t={t} onChange={(effects) => patch({ effects })} />
          </section>
        </>
      ) : (
        <div className="py-6 text-center text-xs text-slate-400">{t('pick_track')}</div>
      )}
      <section>
        <div className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">{t('master_effects')}</div>
        <EffectRack
          effects={project.master.effects}
          catalog={catalog}
          t={t}
          onChange={(effects) => edit((p) => ({ ...p, master: { ...p.master, effects } }))}
        />
      </section>
    </div>
  );
};
