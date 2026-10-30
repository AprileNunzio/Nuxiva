import React, { useEffect, useId, useRef, useState } from 'react';
import { SettingSpec, SettingValue } from '../../../shared/bluetooth/model';
import { fieldClass, useBluetoothI18n } from '../scope';
import { Switch } from './Switch';

interface SettingFieldProps {
  readonly spec: SettingSpec;
  readonly value: SettingValue;
  readonly disabled: boolean;
  readonly onCommit: (value: SettingValue) => void;
}

const COMMIT_DELAY_MS = 350;
const CONTROL = /[\u0000-\u001f\u007f<>"'`\\{}]/g;

function RangeField({ spec, value, disabled, onCommit, id }: SettingFieldProps & { readonly id: string }) {
  const { t } = useBluetoothI18n();
  const current = typeof value === 'number' ? value : 0;
  const [draft, setDraft] = useState(current);
  const commitRef = useRef(onCommit);
  commitRef.current = onCommit;
  useEffect(() => setDraft(current), [current]);
  useEffect(() => {
    if (draft === current) return;
    const timer = window.setTimeout(() => commitRef.current(draft), COMMIT_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [draft, current]);
  if (spec.type !== 'int') return null;
  return (
    <div className="flex items-center gap-3">
      <input
        id={id}
        type="range"
        min={spec.min}
        max={spec.max}
        step={spec.step}
        value={draft}
        disabled={disabled}
        onChange={(event) => setDraft(Number(event.target.value))}
        className="h-2 min-w-0 flex-1 cursor-pointer accent-blue-600 disabled:cursor-not-allowed"
      />
      <output htmlFor={id} className="w-14 shrink-0 text-right font-mono text-xs text-slate-700">
        {t(`setting_${spec.key}_value`, { value: draft })}
      </output>
    </div>
  );
}

function TextField({ spec, value, disabled, onCommit, id }: SettingFieldProps & { readonly id: string }) {
  const { t } = useBluetoothI18n();
  const current = typeof value === 'string' ? value : '';
  const [draft, setDraft] = useState(current);
  useEffect(() => setDraft(current), [current]);
  if (spec.type !== 'text') return null;
  const commit = () => {
    const clean = draft.replace(CONTROL, '').replace(/\s+/g, ' ').trim().slice(0, spec.max);
    if (clean !== current) onCommit(clean);
    setDraft(clean);
  };
  return (
    <input
      id={id}
      type="text"
      value={draft}
      maxLength={spec.max}
      disabled={disabled}
      autoComplete="off"
      spellCheck={false}
      placeholder={t(`setting_${spec.key}_placeholder`)}
      onChange={(event) => setDraft(event.target.value)}
      onBlur={commit}
      onKeyDown={(event) => event.key === 'Enter' && commit()}
      className={fieldClass}
    />
  );
}

function ChoiceField({ spec, value, disabled, onCommit, id }: SettingFieldProps & { readonly id: string }) {
  const { t } = useBluetoothI18n();
  if (spec.type !== 'enum') return null;
  if (spec.options.length <= 3) {
    return (
      <div role="radiogroup" aria-labelledby={`${id}-label`} className="grid grid-flow-col auto-cols-fr gap-1 rounded-xl border border-slate-200 bg-slate-50 p-1">
        {spec.options.map((option) => (
          <button
            key={option}
            type="button"
            role="radio"
            aria-checked={value === option}
            disabled={disabled}
            onClick={() => value !== option && onCommit(option)}
            className={`rounded-lg px-2 py-1.5 text-xs font-semibold transition disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
              value === option ? 'bg-white text-blue-700 shadow-xs ring-1 ring-slate-200' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            {t(`option_${spec.key}_${option}`)}
          </button>
        ))}
      </div>
    );
  }
  return (
    <select id={id} value={String(value)} disabled={disabled} onChange={(event) => onCommit(event.target.value)} className={fieldClass}>
      {spec.options.map((option) => (
        <option key={option} value={option}>
          {t(`option_${spec.key}_${option}`)}
        </option>
      ))}
    </select>
  );
}

export const SettingField: React.FC<SettingFieldProps> = (props) => {
  const { t } = useBluetoothI18n();
  const id = useId();
  const { spec } = props;
  const label = t(`setting_${spec.key}`);
  const hint = t(`setting_${spec.key}_hint`);

  if (spec.type === 'bool') {
    return (
      <div className="flex items-start justify-between gap-3 rounded-xl border border-slate-200 bg-white px-3 py-2.5">
        <span className="min-w-0">
          <span id={`${id}-label`} className="block text-sm font-medium text-slate-900">
            {label}
          </span>
          <span className="block text-[11px] leading-relaxed text-slate-500">{hint}</span>
        </span>
        <Switch checked={props.value === true} disabled={props.disabled} label={label} onChange={props.onCommit} />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-2.5">
      <label id={`${id}-label`} htmlFor={id} className="text-sm font-medium text-slate-900">
        {label}
      </label>
      {spec.type === 'int' && <RangeField {...props} id={id} />}
      {spec.type === 'enum' && <ChoiceField {...props} id={id} />}
      {spec.type === 'text' && <TextField {...props} id={id} />}
      <span className="text-[11px] leading-relaxed text-slate-500">{hint}</span>
    </div>
  );
};
