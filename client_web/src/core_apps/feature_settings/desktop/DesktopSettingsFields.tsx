import React from 'react';
import { Grid2X2, ShieldCheck, Timer, Webcam } from 'lucide-react';
import { MD3Switch } from '../../../shared/components/MD3Switch';
import { useScopedI18n } from '../../../shared/i18n/useScopedI18n';
import { FeatureSetting } from '../../shared/featureTypes';
import { optionValue, SettingReference, SettingsFieldsProps } from '../../shared/SettingsEditor';
import './desktop_settings.css';

const groups = [
  {
    id: 'widgets', icon: Grid2X2, tone: 'bg-primary-container text-on-primary-container',
    keys: ['NUXIVA_SECRETARY', 'NUXIVA_DISPLAY_LEARNING'],
  },
  {
    id: 'privacy', icon: ShieldCheck, tone: 'bg-secondary-container text-on-secondary-container',
    keys: ['NUXIVA_DISPLAY_GUEST_PUBLIC', 'NUXIVA_DISPLAY_TRUST_GUESTS', 'NUXIVA_DISPLAY_ROOM_STRICT'],
  },
  {
    id: 'devices', icon: Webcam, tone: 'bg-tertiary-container text-on-tertiary-container',
    keys: ['NUXIVA_REMOTE_CAMERA_PREVIEW', 'NUXIVA_REMOTE_CAMERA_PROBE', 'NUXIVA_REMOTE_MIC_INPUT'],
  },
  {
    id: 'timing', icon: Timer, tone: 'bg-warning-container text-on-warning-container',
    keys: ['NUXIVA_PRIVACY_AUTOCLOSE', 'NUXIVA_PRIVACY_AWAY_S', 'NUXIVA_PRIVACY_VOICE_S'],
  },
] as const;

const groupedKeys = new Set<string>(groups.flatMap((group) => [...group.keys]));

function isSwitch(setting: FeatureSetting): boolean {
  const options = setting.options?.map(optionValue);
  return setting.type === 'bool' || (setting.type === 'select' && options?.length === 2
    && options.includes('0') && options.includes('1'));
}

export function DesktopSettingsFields({ fields, current, change, renderDefault, busy }: SettingsFieldsProps) {
  const { t } = useScopedI18n('core_apps/feature_settings');
  const byKey = new Map(fields.map((field) => [field.key, field]));
  const extra = fields.filter((field) => !groupedKeys.has(field.key));

  function renderField(setting: FeatureSetting) {
    if (!isSwitch(setting)) return renderDefault(setting);
    return (
      <div className="desktop-switch-row rounded-2xl bg-surface-container-lowest px-3 py-1.5" key={setting.key}>
        <MD3Switch
          label={setting.label}
          description={setting.help}
          checked={current(setting) === '1'}
          disabled={busy}
          onChange={(checked) => change(setting.key, checked ? '1' : '0')}
        />
        <SettingReference setting={setting} />
      </div>
    );
  }

  return (
    <div className="desktop-settings-grid">
      {groups.map(({ id, icon: Icon, tone, keys }) => {
        const settings = keys.flatMap((key) => byKey.get(key) ?? []);
        if (!settings.length) return null;
        return (
          <section key={id} className="min-w-0 rounded-3xl bg-surface-container-low p-4 sm:p-5">
            <header className="mb-4 flex items-start gap-3">
              <span className={`grid size-10 shrink-0 place-items-center rounded-2xl ${tone}`}>
                <Icon className="size-5" aria-hidden="true" />
              </span>
              <div className="min-w-0">
                <h2 className="text-base font-semibold text-on-surface">{t(`desktop_${id}_title`)}</h2>
                <p className="mt-0.5 text-sm text-on-surface-variant">{t(`desktop_${id}_description`)}</p>
              </div>
            </header>
            <div className="grid gap-2">{settings.map(renderField)}</div>
          </section>
        );
      })}
      {extra.length > 0 && (
        <section className="min-w-0 rounded-3xl bg-surface-container-low p-4 sm:p-5">
          <h2 className="mb-3 text-base font-semibold">{t('desktop_other_title')}</h2>
          <div className="grid gap-2">{extra.map(renderField)}</div>
        </section>
      )}
    </div>
  );
}
