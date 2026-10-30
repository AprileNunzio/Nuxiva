import React from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { Btn, Empty, Panel, Toggle, inputClass } from '../shared/kit';
import { actionLabel, contextLabel, gestureLabel } from './labels';
import { GestureBinding, HAND_FILTERS, HandFilter, IDENTIFIER, MODIFIER_POSES } from './types';

type Translate = (key: string, params?: Record<string, string | number>) => string;

interface BindingsPanelProps {
  readonly t: Translate;
  readonly bindings: GestureBinding[];
  readonly catalog: string[];
  readonly actions: string[];
  readonly contexts: string[];
  readonly onChange: (next: GestureBinding[]) => void;
}

const blank = (gesture: string): GestureBinding => ({
  gesture,
  hand: 'any',
  context: '*',
  modifier: null,
  action: 'ui.click',
  args: {},
  confirm: false,
  enabled: true,
});

export const BindingsPanel: React.FC<BindingsPanelProps> = ({ t, bindings, catalog, actions, contexts, onChange }) => {
  const update = (index: number, patch: Partial<GestureBinding>) =>
    onChange(bindings.map((binding, i) => (i === index ? { ...binding, ...patch } : binding)));
  const remove = (index: number) => onChange(bindings.filter((_, i) => i !== index));
  const add = () => onChange([...bindings, blank(catalog[0] || 'tap')]);

  return (
    <Panel
      title={t('bindings_title')}
      actions={
        <Btn onClick={add} disabled={bindings.length >= 256}>
          <Plus className="h-3.5 w-3.5" aria-hidden="true" />
          {t('bindings_add')}
        </Btn>
      }
    >
      <p className="mb-3 text-sm text-slate-600">{t('bindings_hint')}</p>
      <datalist id="hands-actions">
        {actions.map((action) => (
          <option key={action} value={action}>
            {actionLabel(t, action)}
          </option>
        ))}
      </datalist>
      {bindings.length === 0 ? <Empty>{t('bindings_empty')}</Empty> : null}
      <ul className="flex flex-col gap-3">
        {bindings.map((binding, index) => {
          const actionValid = IDENTIFIER.test(binding.action);
          return (
            <li key={index} className="grid gap-2 rounded-xl border border-slate-200 bg-slate-50 p-3 sm:grid-cols-2 xl:grid-cols-6">
              <label className="flex flex-col gap-1 text-xs font-semibold text-slate-600 xl:col-span-2">
                {t('binding_gesture')}
                <select className={inputClass} value={binding.gesture} onChange={(e) => update(index, { gesture: e.target.value })}>
                  {catalog.map((id) => (
                    <option key={id} value={id}>
                      {gestureLabel(t, id)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col gap-1 text-xs font-semibold text-slate-600">
                {t('binding_hand')}
                <select className={inputClass} value={binding.hand} onChange={(e) => update(index, { hand: e.target.value as HandFilter })}>
                  {HAND_FILTERS.map((hand) => (
                    <option key={hand} value={hand}>
                      {t(`hand_${hand}`)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col gap-1 text-xs font-semibold text-slate-600">
                {t('binding_context')}
                <select className={inputClass} value={binding.context} onChange={(e) => update(index, { context: e.target.value })}>
                  {contexts.map((context) => (
                    <option key={context} value={context}>
                      {contextLabel(t, context)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col gap-1 text-xs font-semibold text-slate-600">
                {t('binding_modifier')}
                <select
                  className={inputClass}
                  value={binding.modifier ?? ''}
                  onChange={(e) => update(index, { modifier: e.target.value || null })}
                >
                  <option value="">{t('modifier_none')}</option>
                  {MODIFIER_POSES.map((pose) => (
                    <option key={pose} value={pose}>
                      {t(`name_${pose}`)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col gap-1 text-xs font-semibold text-slate-600">
                {t('binding_action')}
                <input
                  className={`${inputClass} ${actionValid ? '' : 'border-rose-400'}`}
                  list="hands-actions"
                  value={binding.action}
                  maxLength={64}
                  aria-invalid={!actionValid}
                  onChange={(e) => update(index, { action: e.target.value.trim().toLowerCase() })}
                />
              </label>
              <div className="flex flex-wrap items-center justify-between gap-3 sm:col-span-2 xl:col-span-6">
                <div className="flex flex-wrap items-center gap-4 text-xs font-semibold text-slate-600">
                  <span className="flex items-center gap-2">
                    <Toggle checked={binding.enabled} onChange={(value) => update(index, { enabled: value })} label={t('binding_enabled')} />
                    {t('binding_enabled')}
                  </span>
                  <span className="flex items-center gap-2">
                    <Toggle checked={binding.confirm} onChange={(value) => update(index, { confirm: value })} label={t('binding_confirm')} />
                    {t('binding_confirm')}
                  </span>
                </div>
                <Btn tone="rose" onClick={() => remove(index)} title={t('delete')}>
                  <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                  {t('delete')}
                </Btn>
              </div>
            </li>
          );
        })}
      </ul>
    </Panel>
  );
};
