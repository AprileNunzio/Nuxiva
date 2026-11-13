import React, { FormEvent, useState } from 'react';
import { BadgeCheck } from 'lucide-react';
import { Btn, Empty, Field, List, Panel, Pill, Row, formatTime, inputClass } from '../../shared/kit';
import { confirmTrust, requestTrust, untrust } from '../api';
import { TrustRequest, TrustedDevice } from '../types';
import { Run, Translate } from './shared';

interface Props {
  readonly devices: readonly TrustedDevice[];
  readonly busy: boolean;
  readonly lang: string;
  readonly t: Translate;
  readonly run: Run;
  readonly reload: () => void;
}

export const TrustedPanel: React.FC<Props> = ({ devices, busy, lang, t, run, reload }) => {
  const [address, setAddress] = useState('');
  const [label, setLabel] = useState('');
  const [pending, setPending] = useState<TrustRequest | null>(null);
  const [code, setCode] = useState('');
  const [risks, setRisks] = useState(false);

  const ask = async (event: FormEvent) => {
    event.preventDefault();
    if (!address.trim()) {
      return;
    }
    const created = await run(() => requestTrust(address.trim(), label.trim()), 'firewall_trust_failed');
    if (created) {
      setPending(created);
      setCode('');
      setRisks(false);
    }
  };

  const confirm = async (event: FormEvent) => {
    event.preventDefault();
    if (!pending) {
      return;
    }
    if ((await run(() => confirmTrust(pending.id, code.trim(), risks), 'firewall_trust_failed')) !== null) {
      setPending(null);
      setAddress('');
      setLabel('');
      setCode('');
      reload();
    }
  };

  return (
    <Panel title={t('trusted_title')} icon={<BadgeCheck className="h-4 w-4 text-emerald-700" aria-hidden="true" />}>
      <p className="mb-3 text-xs text-slate-500">{t('trusted_hint')}</p>
      {pending ? (
        <form onSubmit={confirm} className="mb-3 flex flex-col gap-2 rounded-2xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
          <p>{t('trusted_confirm', { address: pending.addresses.join(', ') })}</p>
          <p className="font-mono text-lg tracking-widest" aria-label={t('trusted_code_label')}>{pending.code}</p>
          {pending.risks.map((risk) => (
            <Pill key={risk} tone="rose">{t(`risk_${risk}`)}</Pill>
          ))}
          <input className={inputClass} value={code} inputMode="numeric" maxLength={6} autoComplete="off" onChange={(event) => setCode(event.target.value.replace(/\D/g, ''))}
            placeholder={t('trusted_code_placeholder')} aria-label={t('trusted_code_placeholder')} />
          {pending.risks.length > 0 ? (
            <label className="flex items-center gap-2 text-xs">
              <input type="checkbox" checked={risks} onChange={(event) => setRisks(event.target.checked)} />
              {t('trusted_accept_risks')}
            </label>
          ) : null}
          <div className="flex gap-2">
            <Btn type="submit" tone="emerald" busy={busy} disabled={code.length !== 6 || (pending.risks.length > 0 && !risks)}>{t('trusted_confirm_button')}</Btn>
            <Btn tone="slate" onClick={() => setPending(null)}>{t('cancel')}</Btn>
          </div>
        </form>
      ) : (
        <form onSubmit={ask} className="mb-3 flex flex-wrap gap-2">
          <input className={`${inputClass} flex-1`} value={address} maxLength={80} onChange={(event) => setAddress(event.target.value)}
            placeholder={t('block_placeholder')} aria-label={t('block_placeholder')} />
          <div className="w-48">
            <Field label={t('trusted_label')}>
              <input className={inputClass} value={label} maxLength={60} onChange={(event) => setLabel(event.target.value)} />
            </Field>
          </div>
          <Btn type="submit" tone="emerald" busy={busy}>{t('trusted_add')}</Btn>
        </form>
      )}
      {devices.length === 0 ? (
        <Empty>{t('trusted_empty')}</Empty>
      ) : (
        <List>
          {devices.map((device) => (
            <Row key={device.address} actions={<Btn tone="slate" busy={busy} onClick={() => void run(() => untrust(device.address), 'firewall_untrust_failed').then(reload)}>{t('trusted_remove')}</Btn>}>
              <b>{device.label || device.address}</b>
              <span className="ml-2 font-mono text-xs text-slate-600">{device.address}</span>
              <p className="text-[11px] text-slate-500">
                {device.online ? t('online') : t('offline')}{device.since ? ` · ${formatTime(device.since, lang)}` : ''}
              </p>
            </Row>
          ))}
        </List>
      )}
    </Panel>
  );
};
