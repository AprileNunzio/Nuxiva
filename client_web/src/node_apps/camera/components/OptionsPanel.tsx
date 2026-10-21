import React, { useEffect, useState } from 'react';
import { Loader2, Save } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { Panel } from '../../shared/components/ModuleFrame';
import { CameraOptions, CameraSource, saveOptions } from '../data/camerasApi';
import { useCameraI18n } from '../scope';

const ROTATIONS = [0, 90, 180, 270] as const;
type Toggle = 'mirror' | 'motion' | 'photo_on_motion' | 'favorite' | 'hidden';
const TOGGLES: readonly Toggle[] = ['mirror', 'motion', 'photo_on_motion', 'favorite', 'hidden'];

const field = 'w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-cyan-400 focus:outline-none';

export const OptionsPanel: React.FC<{ readonly source: CameraSource; readonly onSaved: () => void }> = ({ source, onSaved }) => {
  const { t } = useCameraI18n();
  const [draft, setDraft] = useState<CameraOptions>(source.options);
  const [saving, setSaving] = useState(false);
  const dirty = JSON.stringify(draft) !== JSON.stringify(source.options);

  useEffect(() => setDraft(source.options), [source.id, source.options]);

  const save = async () => {
    setSaving(true);
    try {
      await saveOptions(source.id, draft);
      onSaved();
    } catch (cause) {
      reportError('node_camera_options_failed', cause);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Panel title={t('options_title')}>
      <div className="grid gap-2 sm:grid-cols-2">
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          {t('option_alias')}
          <input className={field} maxLength={40} value={draft.alias} onChange={(event) => setDraft({ ...draft, alias: event.target.value })} />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          {t('option_room')}
          <input className={field} maxLength={40} value={draft.room} onChange={(event) => setDraft({ ...draft, room: event.target.value })} />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          {t('option_rotate')}
          <select className={field} value={draft.rotate} onChange={(event) => setDraft({ ...draft, rotate: Number(event.target.value) })}>
            {ROTATIONS.map((deg) => (
              <option key={deg} value={deg}>
                {deg}°
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          {t('option_sensitivity', { value: draft.sensitivity })}
          <input
            type="range"
            min={1}
            max={10}
            value={draft.sensitivity}
            disabled={!draft.motion}
            onChange={(event) => setDraft({ ...draft, sensitivity: Number(event.target.value) })}
            className="mt-2 w-full cursor-pointer accent-cyan-400"
          />
        </label>
      </div>
      <div className="mt-2 grid gap-2 sm:grid-cols-2">
        {TOGGLES.map((key) => (
          <label key={key} className="flex cursor-pointer items-center justify-between gap-3 rounded-xl border border-slate-800/80 bg-slate-950/40 px-3 py-2 text-sm text-slate-100">
            {t(`option_${key}`)}
            <input
              type="checkbox"
              role="switch"
              checked={draft[key]}
              disabled={key === 'photo_on_motion' && !draft.motion}
              onChange={(event) => setDraft({ ...draft, [key]: event.target.checked })}
              className="h-5 w-9 cursor-pointer accent-cyan-400"
            />
          </label>
        ))}
      </div>
      <button
        type="button"
        onClick={save}
        disabled={!dirty || saving}
        className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl border border-cyan-400/40 bg-cyan-400/10 px-4 py-2.5 text-sm font-semibold text-cyan-100 transition hover:bg-cyan-400/20 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
      >
        {saving ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Save className="h-4 w-4" aria-hidden="true" />}
        {t('options_save')}
      </button>
    </Panel>
  );
};
