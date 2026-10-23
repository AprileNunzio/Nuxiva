import React, { useState } from 'react';
import { Copy, Eye, EyeOff, KeyRound, Network } from 'lucide-react';
import { Btn, Panel, Pill } from '../../shared/kit';
import { saveSettings } from '../../shared/featureApi';
import { useAction } from '../../shared/useResource';
import { SharesOverview } from '../types';

interface AccessPanelProps {
  readonly data: SharesOverview;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
  readonly onChanged: () => void;
}

const Line: React.FC<{ readonly label: string; readonly value: string; readonly secret?: boolean; readonly copyLabel: string }> = ({ label, value, secret = false, copyLabel }) => {
  const [shown, setShown] = useState(false);
  const copy = () => {
    void navigator.clipboard?.writeText(value).catch(() => undefined);
  };
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
      <div className="min-w-0">
        <span className="block text-[10px] font-semibold uppercase tracking-wider text-slate-500">{label}</span>
        <code className="break-all text-sm text-blue-800">{secret && !shown ? '••••••••••••' : value || '—'}</code>
      </div>
      <div className="flex gap-1.5">
        {secret ? (
          <Btn tone="slate" onClick={() => setShown((current) => !current)} title={label}>
            {shown ? <EyeOff className="h-3.5 w-3.5" aria-hidden="true" /> : <Eye className="h-3.5 w-3.5" aria-hidden="true" />}
          </Btn>
        ) : null}
        <Btn tone="slate" disabled={!value} onClick={copy} title={copyLabel}>
          <Copy className="h-3.5 w-3.5" aria-hidden="true" />
        </Btn>
      </div>
    </div>
  );
};

export const AccessPanel: React.FC<AccessPanelProps> = ({ data, t, onChanged }) => {
  const { busy, run } = useAction(onChanged);
  const online = data.active === 'active' || data.active === 'demo';
  return (
    <Panel
      title={t('access_title')}
      icon={<Network className="h-4 w-4 text-blue-700" aria-hidden="true" />}
      actions={<Pill tone={online ? 'emerald' : 'rose'}>{online ? t('service_on') : t('service_off')}</Pill>}
    >
      <div className="grid gap-2 lg:grid-cols-2">
        <Line label={t('windows_path')} value={data.unc} copyLabel={t('copy')} />
        <Line label={t('unix_path')} value={`smb://${data.ip}/condivisa`} copyLabel={t('copy')} />
        <Line label={t('user')} value={data.user} copyLabel={t('copy')} />
        <Line label={t('password')} value={data.password} secret copyLabel={t('copy')} />
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Btn tone="amber" busy={busy} onClick={() => void run(() => saveSettings('shares', { NUXIVA_SMB_PASSWORD: '' }), 'shares_password_failed')}>
          <KeyRound className="h-3.5 w-3.5" aria-hidden="true" />
          {t('new_password')}
        </Btn>
        <span className="text-xs text-slate-500">{t('new_password_hint')}</span>
      </div>
    </Panel>
  );
};
