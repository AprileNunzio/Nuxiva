import React, { useEffect, useState } from 'react';
import { ChevronDown, RotateCcw, Save } from 'lucide-react';
import { saveRoleChain, saveRoleSettings } from '../../core/brainApi';
import { sameChain } from '../../core/chain';
import { useBrainText, useSectionText } from '../../core/i18n';
import { useBrain } from '../../core/useBrainStore';
import { BrainRef, RoleState, SCOPES, STRATEGIES, RoleScope, RoleStrategy } from '../../core/types';
import { ChainEditor } from '../../ui/ChainEditor';
import { Badge, Button, fieldClass } from '../../ui/primitives';
import { roleIcon } from '../../ui/roleIcons';

interface ContextCardProps {
  readonly role: RoleState;
  readonly known: ReadonlyMap<string, BrainRef>;
}

export const ContextCard: React.FC<ContextCardProps> = ({ role, known }) => {
  const { t } = useSectionText('contexts');
  const base = useBrainText();
  const { pool, commit, action } = useBrain();
  const saved = role.custom ? role.entries.map((entry) => entry.ref) : [];
  const [draft, setDraft] = useState<string[]>(saved);
  const [open, setOpen] = useState(false);
  const savedKey = saved.join('|');
  useEffect(() => setDraft(savedKey ? savedKey.split('|') : []), [savedKey]);

  const Icon = roleIcon(role.id);
  const dirty = !sameChain(draft, saved);
  const key = `role:${role.id}`;
  const busy = action.busy !== null;

  const save = (models: readonly string[]) => commit(key, 'brain_role_failed', () => saveRoleChain(role.id, models));
  const setOption = (change: { scope?: RoleScope; strategy?: RoleStrategy }) =>
    commit(`${key}:options`, 'brain_role_failed', () => saveRoleSettings(role.id, change));

  return (
    <section className="rounded-xl border border-slate-200 bg-white shadow-2xs" aria-labelledby={`ctx-${role.id}`}>
      <header className="flex flex-wrap items-start gap-3 px-4 pt-4 sm:px-5">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
          <Icon className="h-5 w-5" aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1">
          <h3 id={`ctx-${role.id}`} className="flex flex-wrap items-center gap-2 text-sm font-semibold text-slate-900">
            {base.t(`role_${role.id}`)}
            <Badge tone={role.custom ? 'info' : 'neutral'}>{base.t(role.custom ? 'mode_custom' : 'mode_auto')}</Badge>
          </h3>
          <p className="mt-0.5 text-xs text-slate-500">{base.t(`role_${role.id}_hint`)}</p>
          <p className="mt-1.5 text-xs text-slate-700" aria-live="polite">
            {role.active ? t('answering', { model: role.active.model }) : base.t('none_available')}
          </p>
        </div>
      </header>
      <div className="px-4 py-4 sm:px-5">
        {!role.custom && draft.length === 0 && <p className="mb-3 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-600">{t('auto_explain')}</p>}
        <ChainEditor chain={draft} pool={pool} known={known} onChange={setDraft} pickerTitle={t('picker_title', { context: base.t(`role_${role.id}`) })} />
      </div>
      <div className="border-t border-slate-100 px-4 py-3 sm:px-5">
        <button
          type="button"
          aria-expanded={open}
          onClick={() => setOpen(!open)}
          className="flex items-center gap-1.5 text-xs font-medium text-slate-600 hover:text-slate-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40"
        >
          <ChevronDown className={`h-4 w-4 transition ${open ? 'rotate-180' : ''}`} aria-hidden="true" />
          {t('options')}
        </button>
        {open && (
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <label className="flex flex-col gap-1 text-xs text-slate-600">
              {t('scope_label')}
              <select value={role.scope} disabled={busy} onChange={(e) => void setOption({ scope: SCOPES.find((s) => s === e.target.value) ?? 'anywhere' })} className={fieldClass}>
                {SCOPES.map((s) => (
                  <option key={s} value={s}>{t(`scope_${s}`)}</option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1 text-xs text-slate-600">
              {t('strategy_label')}
              <select value={role.strategy} disabled={busy} onChange={(e) => void setOption({ strategy: STRATEGIES.find((s) => s === e.target.value) ?? 'order' })} className={fieldClass}>
                {STRATEGIES.map((s) => (
                  <option key={s} value={s}>{t(`strategy_${s}`)}</option>
                ))}
              </select>
            </label>
          </div>
        )}
      </div>
      {(dirty || role.custom) && (
        <footer className="flex flex-wrap justify-end gap-2 border-t border-slate-100 bg-slate-50 px-4 py-3 sm:px-5">
          {role.custom && (
            <Button icon={RotateCcw} variant="ghost" busy={action.busy === `${key}:reset`} disabled={busy} onClick={() => void commit(`${key}:reset`, 'brain_role_failed', () => saveRoleChain(role.id, []))}>
              {t('reset_auto')}
            </Button>
          )}
          {dirty && (
            <>
              <Button variant="secondary" disabled={busy} onClick={() => setDraft(saved)}>
                {base.t('cancel')}
              </Button>
              <Button variant="primary" icon={Save} busy={action.busy === key} disabled={busy || draft.length === 0} onClick={() => void save(draft)}>
                {base.t('save')}
              </Button>
            </>
          )}
        </footer>
      )}
    </section>
  );
};
