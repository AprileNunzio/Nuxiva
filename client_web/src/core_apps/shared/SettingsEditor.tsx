import React, { useState } from 'react';
import { Btn, Field, inputClass } from './kit';
import { saveSettings } from './featureApi';
import { FeatureRow, FeatureSetting } from './featureTypes';

interface SettingsEditorProps {
  readonly feature: FeatureRow;
  readonly busy: boolean;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
  readonly run: <R>(task: () => Promise<R>, code?: string) => Promise<R | null>;
}

const optionValue = (option: string | { value: string; label: string }) => (typeof option === 'string' ? option : option.value);
const optionLabel = (option: string | { value: string; label: string }) => (typeof option === 'string' ? option : option.label);
const editable = (setting: FeatureSetting) => setting.type !== 'link';

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
        <Field key={setting.key} label={setting.label}>
          {setting.type === 'select' ? (
            <select className={inputClass} value={current(setting)} onChange={(event) => change(setting.key, event.target.value)}>
              {(setting.options ?? []).map((option) => (
                <option key={optionValue(option)} value={optionValue(option)}>
                  {optionLabel(option)}
                </option>
              ))}
            </select>
          ) : setting.type === 'bool' ? (
            <select className={inputClass} value={current(setting)} onChange={(event) => change(setting.key, event.target.value)}>
              <option value="1">{t('on')}</option>
              <option value="0">{t('off')}</option>
            </select>
          ) : (
            <input
              className={inputClass}
              type={setting.type === 'secret' ? 'password' : setting.type === 'number' ? 'number' : setting.type === 'color' ? 'color' : 'text'}
              autoComplete="off"
              value={current(setting)}
              maxLength={500}
              onChange={(event) => change(setting.key, event.target.value)}
            />
          )}
          {setting.help && <span className="text-[11px] font-normal text-slate-500">{setting.help}</span>}
        </Field>
      ))}
      <div style={{gridColumn:'1 / -1'}}>
        <Btn tone="emerald" busy={busy} disabled={!dirty} onClick={() => void save()}>
          {t('save')}
        </Btn>
      </div>
    </div>
  );
};
