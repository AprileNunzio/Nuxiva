import React, { useEffect, useMemo, useState } from 'react';
import { ArrowDown, ArrowUp, CircleDot, Loader2, Plus, RotateCcw, Save, Sparkles, SlidersHorizontal, X } from 'lucide-react';
import { ActionHandle } from '../../shared/hooks/useAction';
import { BrainOverview, RoleState, saveRole } from '../data/brainApi';
import { BrainRef, REF } from '../data/parse';
import { ORIGIN_TONE, chipButton, fieldClass, roleIcon, useBrainI18n } from '../scope';

interface RoleCardProps {
  readonly role: RoleState;
  readonly pool: readonly BrainRef[];
  readonly action: ActionHandle;
  readonly onSaved: (overview: BrainOverview) => void;
}

export const RoleCard: React.FC<RoleCardProps> = ({ role, pool, action, onSaved }) => {
  const { t } = useBrainI18n();
  const Icon = roleIcon(role.id);
  const [draft, setDraft] = useState<string[]>(role.entries.map((e) => e.ref));
  const [pick, setPick] = useState('');
  const [customMode, setCustomMode] = useState(false);
  const [customInput, setCustomInput] = useState('');
  useEffect(() => setDraft(role.entries.map((e) => e.ref)), [role.entries]);

  const known = useMemo(() => new Map([...pool, ...role.entries].map((r) => [r.ref, r])), [pool, role.entries]);
  const dirty = draft.join('|') !== role.entries.map((e) => e.ref).join('|');
  const choices = pool.filter((r) => !draft.includes(r.ref));
  const busy = action.busy !== null;

  const move = (index: number, delta: number) => {
    const next = [...draft];
    const [item] = next.splice(index, 1);
    next.splice(index + delta, 0, item);
    setDraft(next);
  };

  const addCustom = () => {
    const raw = customInput.trim();
    if (!raw) {
      return;
    }
    const resolved = raw.startsWith('cloud:')
      ? raw
      : raw.startsWith('gemini')
        ? `cloud:gemini/${raw}`
        : raw.startsWith('claude')
          ? `cloud:anthropic/${raw}`
          : raw.startsWith('gpt-') || raw.startsWith('o3') || raw.startsWith('o4')
            ? `cloud:openai/${raw}`
            : raw;
    if (REF.test(resolved) && !draft.includes(resolved) && draft.length < 12) {
      setDraft([...draft, resolved]);
      setCustomInput('');
      setCustomMode(false);
    }
  };

  const save = async (models: string[]) => {
    const result = await action.run(`role:${role.id}`, () => saveRole(role.id, models), 'node_brain_role_failed');
    if (result) {
      onSaved(result);
    }
  };

  return (
    <li className="rounded-2xl border border-slate-800/80 bg-slate-950/40 p-3">
      <div className="flex items-start gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-cyan-400/40 bg-cyan-400/10">
          <Icon className="h-4 w-4 text-cyan-200" aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="flex flex-wrap items-center gap-2 text-sm font-semibold text-slate-100">
            {t(`role_${role.id}`)}
            <span className="rounded-full border border-slate-700 px-1.5 py-0.5 text-[10px] font-normal text-slate-400">
              {t(role.custom ? 'role_custom' : 'role_auto')}
            </span>
          </p>
          <p className="text-[11px] text-slate-500">{t(`role_${role.id}_hint`)}</p>
          <p className="mt-1 truncate text-[11px] text-slate-400">
            {role.active ? t('role_active', { model: role.active.model }) : t('role_none_active')}
          </p>
        </div>
      </div>
      <ol className="mt-3 flex flex-col gap-1.5">
        {draft.map((ref, index) => {
          const info = known.get(ref);
          return (
            <li key={ref} className="flex items-center gap-2 rounded-lg border border-slate-800/80 bg-slate-900/50 px-2 py-1.5">
              <span className="w-4 shrink-0 font-mono text-[11px] text-cyan-300">{index + 1}</span>
              <CircleDot className={`h-3 w-3 shrink-0 ${info?.available === false ? 'text-rose-400' : 'text-emerald-300'}`} aria-label={t(info?.available === false ? 'unavailable' : 'available')} />
              <span className="min-w-0 flex-1 truncate font-mono text-xs text-slate-200">{info?.model ?? ref}</span>
              <span className={`hidden shrink-0 rounded-full border px-1.5 py-0.5 text-[10px] sm:inline ${ORIGIN_TONE[info?.origin ?? 'local']}`}>{t(`origin_${info?.origin ?? 'local'}`)}</span>
              <button type="button" aria-label={t('move_up')} disabled={index === 0} onClick={() => move(index, -1)} className="rounded p-1 text-slate-400 hover:text-cyan-200 disabled:opacity-30">
                <ArrowUp className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
              <button type="button" aria-label={t('move_down')} disabled={index === draft.length - 1} onClick={() => move(index, 1)} className="rounded p-1 text-slate-400 hover:text-cyan-200 disabled:opacity-30">
                <ArrowDown className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
              <button type="button" aria-label={t('remove')} onClick={() => setDraft(draft.filter((r) => r !== ref))} className="rounded p-1 text-slate-500 hover:text-rose-300">
                <X className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            </li>
          );
        })}
      </ol>
      {!customMode ? (
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <select aria-label={t('add_model')} value={pick} onChange={(event) => setPick(event.target.value)} className={`${fieldClass} min-w-0 flex-1 py-1.5 text-xs`}>
            <option value="">{t('add_model')}</option>
            {choices.map((r) => (
              <option key={r.ref} value={r.ref} disabled={!r.available}>
                {r.model} · {t(`origin_${r.origin}`)}
              </option>
            ))}
          </select>
          <button
            type="button"
            disabled={!pick || draft.length >= 12}
            onClick={() => {
              setDraft([...draft, pick]);
              setPick('');
            }}
            className={`${chipButton} border-slate-700 text-slate-200 hover:border-cyan-400/60`}
          >
            <Plus className="h-3.5 w-3.5" aria-hidden="true" />
            {t('add')}
          </button>
          <button
            type="button"
            title={t('custom_model_toggle')}
            aria-label={t('custom_model_toggle')}
            onClick={() => setCustomMode(true)}
            className={`${chipButton} border-slate-800 text-slate-400 hover:border-cyan-400/40 hover:text-cyan-200`}
          >
            <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        </div>
      ) : (
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <input
            type="text"
            value={customInput}
            onChange={(e) => setCustomInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addCustom())}
            placeholder={t('custom_model_id_placeholder')}
            aria-label={t('custom_model_id_placeholder')}
            className={`${fieldClass} min-w-0 flex-1 py-1.5 text-xs font-mono`}
          />
          <button
            type="button"
            disabled={!customInput.trim() || draft.length >= 12}
            onClick={addCustom}
            className={`${chipButton} border-cyan-400/50 bg-cyan-400/10 text-cyan-200 hover:bg-cyan-400/20`}
          >
            <Plus className="h-3.5 w-3.5" aria-hidden="true" />
            {t('custom_model_add')}
          </button>
          <button
            type="button"
            title={t('catalog_model_toggle')}
            aria-label={t('catalog_model_toggle')}
            onClick={() => {
              setCustomMode(false);
              setCustomInput('');
            }}
            className={`${chipButton} border-slate-800 text-slate-400 hover:border-slate-600 hover:text-white`}
          >
            <SlidersHorizontal className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        </div>
      )}
      <div className="mt-2 flex flex-wrap gap-2">
        <button type="button" disabled={!dirty || busy} onClick={() => void save(draft)} className={`${chipButton} border-cyan-400/50 bg-cyan-400/10 text-cyan-100 hover:bg-cyan-400/20`}>
          {action.busy === `role:${role.id}` ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : <Save className="h-3.5 w-3.5" aria-hidden="true" />}
          {t('save')}
        </button>
        {role.custom && (
          <button type="button" disabled={busy} onClick={() => void save([])} className={`${chipButton} border-slate-700 text-slate-300 hover:border-amber-400/60`}>
            <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
            {t('reset_auto')}
          </button>
        )}
      </div>
    </li>
  );
};
