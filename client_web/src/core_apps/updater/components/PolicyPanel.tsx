import React, { FormEvent, useEffect, useState } from 'react';
import { CalendarClock, Loader2, Save } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { savePolicy } from '../api';
import { UpdatePolicy, UpdaterStatus } from '../types';
import { buttonClass, formatDateTime, panelClass, useUpdaterI18n } from '../scope';

interface PolicyPanelProps {
  readonly status: UpdaterStatus;
  readonly onStatus: (status: UpdaterStatus) => void;
}

type ToggleKey = 'auto_update' | 'sync_nodes' | 'require_ci';
const TOGGLES: readonly ToggleKey[] = ['auto_update', 'sync_nodes', 'require_ci'];

export const PolicyPanel: React.FC<PolicyPanelProps> = ({ status, onStatus }) => {
  const { t, lang } = useUpdaterI18n();
  const [draft, setDraft] = useState<UpdatePolicy>(status.policy);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const dirty = JSON.stringify(draft) !== JSON.stringify(status.policy);

  useEffect(() => {
    if (!dirty) {
      setDraft(status.policy);
    }
  }, [status.policy]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setSaved(false);
    try {
      onStatus(await savePolicy(draft));
      setSaved(true);
    } catch (cause) {
      reportError('updater_policy_failed', cause);
    } finally {
      setSaving(false);
    }
  };

  const nightly = draft.window !== '';
  return (
    <form onSubmit={submit} className={panelClass} aria-labelledby="upd-policy-title">
      <h2 id="upd-policy-title" className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
        <CalendarClock className="h-4 w-4 text-cyan-300" aria-hidden="true" />
        {t('policy_title')}
      </h2>
      <div className="flex flex-col gap-3">
        {TOGGLES.map((key) => (
          <label key={key} className="flex cursor-pointer items-start justify-between gap-4 rounded-xl border border-slate-800/80 bg-slate-950/40 px-3 py-2.5">
            <span>
              <span className="block text-sm font-medium text-slate-100">{t(`policy_${key}`)}</span>
              <span className="block text-xs text-slate-500">{t(`policy_${key}_hint`)}</span>
            </span>
            <input
              type="checkbox"
              role="switch"
              checked={draft[key]}
              onChange={(event) => setDraft({ ...draft, [key]: event.target.checked })}
              className="mt-1 h-5 w-9 shrink-0 cursor-pointer accent-cyan-400"
            />
          </label>
        ))}
        <fieldset className="rounded-xl border border-slate-800/80 bg-slate-950/40 px-3 py-2.5" disabled={!draft.auto_update}>
          <legend className="sr-only">{t('policy_window')}</legend>
          <label className="flex items-center justify-between gap-4">
            <span className="text-sm font-medium text-slate-100">{t('policy_window')}</span>
            <input
              type="checkbox"
              role="switch"
              checked={nightly}
              onChange={(event) => setDraft({ ...draft, window: event.target.checked ? '03:00' : '' })}
              className="h-5 w-9 cursor-pointer accent-cyan-400"
            />
          </label>
          {nightly && (
            <input
              type="time"
              value={draft.window}
              required
              onChange={(event) => setDraft({ ...draft, window: event.target.value })}
              aria-label={t('policy_window_time')}
              className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm text-white focus:border-cyan-400 focus:outline-none"
            />
          )}
          <p className="mt-1 text-xs text-slate-500">
            {nightly ? t('policy_window_hint', { time: draft.window }) : t('policy_window_anytime')}
          </p>
        </fieldset>
        <label className="flex items-center justify-between gap-4 rounded-xl border border-slate-800/80 bg-slate-950/40 px-3 py-2.5">
          <span className="text-sm font-medium text-slate-100">{t('policy_interval')}</span>
          <input
            type="number"
            min={1}
            max={1440}
            value={draft.interval_minutes}
            onChange={(event) => setDraft({ ...draft, interval_minutes: Math.max(1, Math.min(1440, Number(event.target.value) || 1)) })}
            className="w-24 rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-right font-mono text-sm text-white focus:border-cyan-400 focus:outline-none"
          />
        </label>
        {status.next_window && (
          <p className="text-xs text-cyan-200/80">{t('policy_next', { when: formatDateTime(status.next_window, lang) ?? '' })}</p>
        )}
        <button
          type="submit"
          disabled={!dirty || saving}
          className={`${buttonClass} border-cyan-400/40 bg-cyan-400/10 text-cyan-100 hover:bg-cyan-400/20`}
        >
          {saving ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Save className="h-4 w-4" aria-hidden="true" />}
          {t(saved && !dirty ? 'policy_saved' : 'policy_save')}
        </button>
      </div>
    </form>
  );
};
