import React, { useEffect, useId, useState } from 'react';
import { Save } from 'lucide-react';
import { useBrainText, useSectionText } from '../../core/i18n';
import {
  PRIVACY_PROFILES,
  PRIVACY_REACH,
  PolicyChoice,
  PrivacyPolicy,
  PrivacyReach,
  coherent,
  presetPolicy,
} from '../../core/privacyApi';
import { Button, fieldClass } from '../../ui/primitives';

export type Fallback = 'auto' | 'inherit';
type Option = (typeof PRIVACY_PROFILES)[number] | 'custom' | Fallback;

interface PolicyPickerProps {
  readonly fallback: Fallback;
  readonly current: PrivacyPolicy | null;
  readonly inherited: PrivacyPolicy;
  readonly busy: boolean;
  readonly disabled: boolean;
  readonly onSave: (choice: PolicyChoice) => void;
}

const optionOf = (policy: PrivacyPolicy | null, fallback: Fallback): Option => (policy ? policy.profile : fallback);

export const PolicyPicker: React.FC<PolicyPickerProps> = ({ fallback, current, inherited, busy, disabled, onSave }) => {
  const { t } = useSectionText('privacy');
  const base = useBrainText();
  const group = useId();
  const [option, setOption] = useState<Option>(optionOf(current, fallback));
  const [custom, setCustom] = useState<PrivacyPolicy>(current ?? { ...inherited, profile: 'custom' });
  const savedKey = JSON.stringify(current);

  useEffect(() => {
    setOption(optionOf(current, fallback));
    setCustom(current ?? { ...inherited, profile: 'custom' });
  }, [savedKey]);

  const effective: PrivacyPolicy =
    option === fallback ? inherited : option === 'custom' ? { ...custom, profile: 'custom' } : presetPolicy(option as (typeof PRIVACY_PROFILES)[number]);
  const valid = coherent(effective);
  const changed = option !== optionOf(current, fallback) || (option === 'custom' && JSON.stringify({ ...custom, profile: 'custom' }) !== savedKey);
  const choice: PolicyChoice = option === fallback ? { profile: fallback } : effective;
  const options: readonly Option[] = [fallback, ...PRIVACY_PROFILES, 'custom'];

  const reachSelect = (level: 'personal' | 'sensitive') => (
    <label className="flex min-w-0 flex-1 flex-col gap-1 text-xs font-medium text-slate-700">
      {t(`level_${level}`)}
      <select
        value={effective[level]}
        disabled={option !== 'custom' || disabled}
        onChange={(e) => setCustom({ ...custom, [level]: e.target.value as PrivacyReach })}
        className={fieldClass}
      >
        {PRIVACY_REACH.map((reach) => (
          <option key={reach} value={reach}>
            {t(`reach_${reach}`)}
          </option>
        ))}
      </select>
    </label>
  );

  return (
    <div className="flex flex-col gap-3">
      <fieldset className="flex flex-col gap-2">
        <legend className="sr-only">{t('profile_label')}</legend>
        <div className="flex flex-wrap gap-2">
          {options.map((value) => {
            const id = `${group}-${value}`;
            const selected = option === value;
            return (
              <label
                key={value}
                htmlFor={id}
                className={`flex min-h-[40px] cursor-pointer items-center rounded-lg border px-3 py-2 text-sm transition focus-within:ring-2 focus-within:ring-blue-500/40 ${
                  selected ? 'border-blue-600 bg-blue-50 font-semibold text-blue-900' : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'
                }`}
              >
                <input id={id} type="radio" name={group} value={value} checked={selected} disabled={disabled} onChange={() => setOption(value)} className="sr-only" />
                {t(`profile_${value}`)}
              </label>
            );
          })}
        </div>
        <p className="text-xs leading-relaxed text-slate-500">{t(`profile_${option}_hint`)}</p>
      </fieldset>
      <div className="flex flex-col gap-3 sm:flex-row">
        {reachSelect('personal')}
        {reachSelect('sensitive')}
      </div>
      {!valid && <p role="alert" className="text-xs text-rose-700">{t('sensitive_looser')}</p>}
      <div className="flex justify-end">
        <Button variant="primary" icon={Save} busy={busy} disabled={disabled || !valid || !changed} onClick={() => onSave(choice)}>
          {base.t('save')}
        </Button>
      </div>
    </div>
  );
};
