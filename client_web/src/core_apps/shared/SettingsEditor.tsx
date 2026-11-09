import React, { useState } from 'react';
import { ArrowUpRight, Settings } from 'lucide-react';
import { windowStore } from '../../app_shell/window_manager/WindowStore';
import { Btn, Field, inputClass } from './kit';
import { saveSettings } from './featureApi';
import { FeatureRow, FeatureSetting } from './featureTypes';

interface SettingsEditorProps {
  readonly feature: FeatureRow;
  readonly busy: boolean;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
  readonly run: <R>(task: () => Promise<R>, code?: string) => Promise<R | null>;
}

export interface SettingsFieldsProps {
  readonly fields: readonly FeatureSetting[];
  readonly current: (setting: FeatureSetting) => string;
  readonly change: (key: string, value: string) => void;
  readonly renderDefault: (setting: FeatureSetting) => React.ReactNode;
  readonly busy: boolean;
}

export const optionValue = (option: string | { value: string; label: string }) => (typeof option === 'string' ? option : option.value);
const optionLabel = (option: string | { value: string; label: string }) => (typeof option === 'string' ? option : option.label);
const editable = (setting: FeatureSetting) => setting.type !== 'link';

export function SettingReference({ setting }: { readonly setting: FeatureSetting }) {
  if (!setting.see || !setting.see_name) return null;
  return (
    <button
      type="button"
      onClick={() => windowStore.openWindow({ appId: 'feature_settings', instanceKey: setting.see })}
      className="inline-flex items-center gap-1.5 self-start text-xs font-medium text-primary hover:underline focus-visible:underline"
    >
      <Settings className="h-3.5 w-3.5" aria-hidden="true" />
      {setting.see_name}
      <ArrowUpRight className="h-3 w-3" aria-hidden="true" />
    </button>
  );
}

export function SettingField({ setting, value, busy, t, onChange }: {
  readonly setting: FeatureSetting;
  readonly value: string;
  readonly busy: boolean;
  readonly t: SettingsEditorProps['t'];
  readonly onChange: (value: string) => void;
}) {
  return (
    <Field label={setting.label}>
      {setting.type === 'select' || setting.type === 'bool' ? (
        <select className={inputClass} disabled={busy} value={value} onChange={(event) => onChange(event.target.value)}>
          {(setting.type === 'bool' ? [{ value: '1', label: t('on') }, { value: '0', label: t('off') }] : setting.options ?? [])
            .map((option) => <option key={optionValue(option)} value={optionValue(option)}>{optionLabel(option)}</option>)}
        </select>
      ) : (
        <input
          className={inputClass}
          type={setting.type === 'secret' ? 'password' : setting.type === 'number' ? 'number' : setting.type === 'color' ? 'color' : 'text'}
          autoComplete="off"
          disabled={busy}
          value={value}
          maxLength={500}
          onChange={(event) => onChange(event.target.value)}
        />
      )}
      {setting.help && <span className="text-xs font-normal text-on-surface-variant">{setting.help}</span>}
      <SettingReference setting={setting} />
    </Field>
  );
}

export const SettingsEditor: React.FC<SettingsEditorProps> = ({ feature, busy, t, run }) => {
  const [draft, setDraft] = useState<Record<string, string>>({});
  const fields = feature.settings.filter(editable);
  const current = (setting: FeatureSetting) => draft[setting.key] ?? feature.values[setting.key] ?? setting.default ?? '';
  const dirty = Object.keys(draft).length > 0;

  const change = (key: string, value: string) => setDraft((state) => ({ ...state, [key]: value }));

  const save = async () => {
    if ((await run(() => saveSettings(feature.id, draft), 'features_settings_failed')) !== null) {
      setDraft({});
    }
  };

  if (fields.length === 0) {
    return <p className="text-xs text-slate-500">{t('no_settings')}</p>;
  }

  return (
    <div className="os-settings-grid">
      {fields.map((setting) => (
        <SettingField key={setting.key} setting={setting} value={current(setting)} busy={busy} t={t}
          onChange={(value) => change(setting.key, value)} />
      ))}
      <div style={{gridColumn:'1 / -1'}}>
        <Btn tone="emerald" busy={busy} disabled={!dirty} onClick={() => void save()}>
          {t('save')}
        </Btn>
      </div>
    </div>
  );
};
