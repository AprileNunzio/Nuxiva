import { PAGE_CLASS } from '../../../shared/ui/layout';
import React from 'react';
import { Check, Grid2X2, ShieldCheck, Unlock } from 'lucide-react';
import { MD3SegmentedButton } from '../../../shared/components/MD3SegmentedButton';
import { useScopedI18n } from '../../../shared/i18n/useScopedI18n';
import { FeatureRow } from '../../shared/featureTypes';
import { SettingField, SettingReference } from '../../shared/SettingsEditor';
import { Btn } from '../../shared/kit';
import { DesktopSettingsFields } from './DesktopSettingsFields';
import { useDesktopAutosave } from './useDesktopAutosave';

const protectionKey = 'NUXIVA_DISPLAY_PRESENCE_GATE';

export function DesktopSettings({ feature }: { readonly feature: FeatureRow }) {
  const { t } = useScopedI18n('core_apps/feature_settings');
  const { current, change, pending, failed, saved } = useDesktopAutosave(feature);
  const protection = feature.settings.find((setting) => setting.key === protectionKey);
  const fields = feature.settings.filter((setting) => setting.key !== protectionKey && setting.type !== 'link');
  const failures = Object.entries(failed);

  return (
    <div className={`${PAGE_CLASS} gap-5`}>
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-outline-variant pb-5">
        <div className="flex min-w-0 items-start gap-3">
          <span className="grid size-12 shrink-0 place-items-center rounded-2xl bg-primary-container text-on-primary-container">
            <Grid2X2 className="size-6" aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <h1 className="text-xl font-semibold text-on-surface">{feature.name}</h1>
            <p className="mt-1 max-w-xl text-sm text-on-surface-variant">{feature.description}</p>
          </div>
        </div>
        <p role="status" className="flex items-center gap-1.5 text-sm text-on-surface-variant">
          {!pending && saved && !failures.length && <Check className="size-4 text-success" aria-hidden="true" />}
          {t(pending ? 'desktop_saving' : failures.length ? 'desktop_save_failed' : saved ? 'desktop_saved' : 'desktop_autosave')}
        </p>
      </header>

      {failures.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-error-container p-3 text-on-error-container" role="alert">
          <span>{t('desktop_retry_description')}</span>
          <Btn disabled={pending > 0} onClick={() => failures.forEach(([key, value]) => change(key, value))}>
            {t('desktop_retry')}
          </Btn>
        </div>
      )}

      {protection && (
        <section className="space-y-3 rounded-3xl bg-secondary-container p-4 text-on-secondary-container sm:p-5">
          <h2 className="text-base font-semibold">{t('desktop_protection_title')}</h2>
          <MD3SegmentedButton
            className="desktop-mode-segments"
            ariaLabel={t('desktop_protection_title')}
            value={current(protection)}
            options={[
              { value: '1', label: t('desktop_protected'), icon: <ShieldCheck className="size-4" /> },
              { value: '0', label: t('desktop_open'), icon: <Unlock className="size-4" /> },
            ]}
            onChange={(value) => { if (value !== current(protection)) change(protection.key, value); }}
          />
          <p className="text-sm">{t(current(protection) === '1' ? 'desktop_protected_hint' : 'desktop_open_hint')}</p>
          {protection.help && <details className="text-sm">
            <summary className="cursor-pointer font-medium">{t('details')}</summary>
            <p className="mt-2">{protection.help}</p>
          </details>}
          <SettingReference setting={protection} />
        </section>
      )}

      <DesktopSettingsFields
        fields={fields}
        current={current}
        change={change}
        busy={false}
        renderDefault={(setting) => (
          <div key={setting.key} className="rounded-2xl bg-surface-container-lowest p-3">
            <SettingField setting={setting} value={current(setting)} busy={false} t={t}
              onChange={(value) => change(setting.key, value)} />
          </div>
        )}
      />
    </div>
  );
}
