import React, { useState } from 'react';
import { ChevronDown, Pin } from 'lucide-react';
import { Btn, Pill, Row, inputClass } from '../../shared/kit';
import { setMode, setPinned } from '../../shared/featureApi';
import { FeatureRow } from '../../shared/featureTypes';
import { SettingsEditor } from '../../shared/SettingsEditor';

interface FeatureCardProps {
  readonly feature: FeatureRow;
  readonly busy: boolean;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
  readonly run: <R>(task: () => Promise<R>, code?: string) => Promise<R | null>;
}

export const FeatureCard: React.FC<FeatureCardProps> = ({ feature, busy, t, run }) => {
  const [open, setOpen] = useState(false);

  return (
    <Row
      actions={
        <>
          {feature.id === 'voicestudio' && <Btn onClick={() => setOpen(true)}>{t('studio_open')}</Btn>}
          <select
            className={`${inputClass} w-36`}
            value={feature.state.mode}
            disabled={busy}
            aria-label={t('mode')}
            onChange={(event) => void run(() => setMode(feature.id, event.target.value), 'features_mode_failed')}
          >
            <option value="auto">{t('mode_auto')}</option>
            <option value="1">{t('mode_on')}</option>
            <option value="0">{t('mode_off')}</option>
          </select>
          <Btn tone={feature.pinned ? 'amber' : 'slate'} busy={busy} onClick={() => void run(() => setPinned(feature.id, !feature.pinned), 'features_pin_failed')} title={t('pin')}>
            <Pin className="h-3.5 w-3.5" aria-hidden="true" />
          </Btn>
          <Btn tone="slate" onClick={() => setOpen((value) => !value)} title={t('details')}>
            <ChevronDown className={`h-3.5 w-3.5 transition ${open ? 'rotate-180' : ''}`} aria-hidden="true" />
          </Btn>
        </>
      }
    >
      <div className="flex flex-wrap items-center gap-2">
        <span aria-hidden="true">{feature.icon}</span>
        <b>{feature.name}</b>
        <Pill tone={feature.state.enabled ? 'emerald' : 'slate'}>{feature.state.enabled ? t('running') : t('stopped')}</Pill>
        {feature.new ? <Pill tone="cyan">{t('new')}</Pill> : null}
      </div>
      <p className="mt-1 text-xs text-slate-500">{feature.state.reason}</p>
      {open ? (
        <div className="mt-3 flex flex-col gap-3 border-t border-slate-200 pt-3">
          <p className="text-sm text-slate-700">{feature.description}</p>
          {feature.capabilities.length ? (
            <ul className="list-disc space-y-0.5 pl-5 text-xs text-slate-600">
              {feature.capabilities.map((capability) => (
                <li key={capability}>{capability}</li>
              ))}
            </ul>
          ) : null}
          <SettingsEditor feature={feature} busy={busy} t={t} run={run} />
        </div>
      ) : null}
    </Row>
  );
};
