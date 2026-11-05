import React from 'react';
import { Download, Lock, ShieldAlert, ShieldCheck } from 'lucide-react';
import { chipClass, fieldClass, primaryClass, usePeopleI18n } from '../scope';
import { caDownloadUrl, secureAdminUrl } from './secureOrigin';
import { AccessState, MediaDeviceOption, MediaKind } from './useMediaAccess';

interface Props {
  readonly kind: MediaKind;
  readonly state: AccessState;
  readonly devices: readonly MediaDeviceOption[];
  readonly deviceId: string;
  readonly active: boolean;
  readonly onRequest: (deviceId?: string) => void;
  readonly onRelease: () => void;
  readonly toggle?: boolean;
}

const TONE: Record<AccessState, string> = {
  checking: 'text-slate-600',
  prompt: 'text-slate-700',
  granted: 'text-emerald-700',
  denied: 'text-rose-700',
  insecure: 'text-amber-800',
  unsupported: 'text-rose-700',
  missing: 'text-amber-800',
  busy: 'text-amber-800',
  failed: 'text-rose-700',
};

export const DeviceAccess: React.FC<Props> = ({ kind, state, devices, deviceId, active, onRequest, onRelease, toggle = true }) => {
  const { t } = usePeopleI18n();
  const secureUrl = state === 'insecure' ? secureAdminUrl() : null;
  const Icon = state === 'granted' ? ShieldCheck : state === 'insecure' ? Lock : ShieldAlert;
  const blocked = state === 'insecure' || state === 'unsupported';
  return (
    <div className="flex flex-col gap-3">
      <p role="status" aria-live="polite" className={`flex items-start gap-2 text-sm ${TONE[state]}`}>
        <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
        <span>{t(`dev_state_${state}`, { device: t(`dev_kind_${kind}`) })}</span>
      </p>
      {state === 'insecure' && (
        <div className="flex flex-wrap gap-2">
          {secureUrl && (
            <a href={secureUrl} className={primaryClass}>
              <Lock className="h-4 w-4" aria-hidden="true" />
              {t('dev_open_secure')}
            </a>
          )}
          <a href={caDownloadUrl()} download className={`${chipClass} border-slate-300 py-2 text-slate-800`}>
            <Download className="h-3.5 w-3.5" aria-hidden="true" />
            {t('dev_download_ca')}
          </a>
          <p className="w-full text-[11px] text-slate-500">{t('dev_ca_hint')}</p>
        </div>
      )}
      {!blocked && (toggle || devices.length > 1) && (
        <div className="flex flex-wrap items-end gap-2">
          {devices.length > 1 && (
            <label className="flex min-w-[12rem] flex-1 flex-col gap-1 text-xs text-slate-600">
              {t(`dev_pick_${kind}`)}
              <select value={deviceId} onChange={(event) => onRequest(event.target.value)} className={fieldClass}>
                {devices.map((d) => (
                  <option key={d.id || d.index} value={d.id}>
                    {d.label || t('dev_device_n', { n: d.index })}
                  </option>
                ))}
              </select>
            </label>
          )}
          {!toggle ? null : active ? (
            <button type="button" onClick={onRelease} className={`${chipClass} border-slate-300 py-2 text-slate-800`}>
              {t(`dev_off_${kind}`)}
            </button>
          ) : (
            <button type="button" disabled={state === 'checking'} onClick={() => onRequest()} className={primaryClass}>
              {t(state === 'granted' ? `dev_on_${kind}` : 'dev_allow')}
            </button>
          )}
        </div>
      )}
      {state === 'denied' && <p className="text-[11px] text-slate-500">{t('dev_denied_help')}</p>}
      <p className="text-[11px] text-slate-500">{t('dev_privacy')}</p>
    </div>
  );
};
