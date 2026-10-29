import React from 'react';
import { Radio, Signal, SignalHigh, SignalLow, SignalMedium, SignalZero } from 'lucide-react';
import { GsmModem } from '../types';

interface GsmModemCardProps {
  readonly modem: GsmModem | null;
  readonly t: (key: string) => string;
}

function getSignalIcon(bars: number) {
  if (bars >= 4) return Signal;
  if (bars === 3) return SignalHigh;
  if (bars === 2) return SignalMedium;
  if (bars === 1) return SignalLow;
  return SignalZero;
}

export const GsmModemCard: React.FC<GsmModemCardProps> = ({ modem, t }) => {
  if (!modem) {
    return (
      <div className="rounded-2xl border border-slate-200/90 bg-white p-5 flex items-center gap-3 text-slate-600 shadow-2xs">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-slate-100 text-slate-400">
          <Radio className="h-5 w-5" />
        </div>
        <div className="flex flex-col">
          <strong className="text-sm font-semibold text-slate-800">{t('gsm_modem_title')}</strong>
          <span className="text-xs text-slate-500">{t('no_gsm_modem_detected')}</span>
        </div>
      </div>
    );
  }

  const SignalIcon = getSignalIcon(modem.signal_bars);

  return (
    <div className="rounded-2xl border border-slate-200/90 bg-white p-4 sm:p-5 shadow-2xs">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-purple-200 bg-purple-50 text-purple-600">
            <Radio className="h-5 w-5" />
          </span>
          <div>
            <div className="flex items-center gap-2">
              <strong className="text-sm font-semibold text-slate-900">{t('gsm_modem_title')}</strong>
              <span className="rounded-full border border-purple-200 bg-purple-50 px-2 py-0.5 font-mono text-[9px] uppercase font-bold text-purple-700">
                {modem.technology}
              </span>
              <span
                className={`rounded-full border px-2 py-0.5 font-mono text-[9px] uppercase font-semibold ${
                  modem.is_connected
                    ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                    : 'border-amber-200 bg-amber-50 text-amber-700'
                }`}
              >
                {modem.is_connected ? t('gsm_connected') : t('gsm_standby')}
              </span>
            </div>
            <span className="text-xs text-slate-500">{modem.operator}</span>
          </div>
        </div>

        <div className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs">
          <SignalIcon className={`h-4 w-4 ${modem.signal_bars >= 3 ? 'text-emerald-600' : 'text-amber-600'}`} />
          <span className="font-mono text-slate-700 font-medium">{modem.signal_dbm} dBm</span>
          <span className="text-slate-400 font-mono text-[10px]">({modem.signal_bars}/5)</span>
        </div>
      </div>

      <div className="grid gap-2 sm:grid-cols-3 text-xs">
        <div className="rounded-xl border border-slate-200/80 bg-slate-50/70 p-2.5">
          <span className="block text-[10px] text-slate-500 uppercase font-semibold tracking-wider">{t('gsm_apn')}</span>
          <strong className="mt-0.5 block font-mono text-slate-800">{modem.apn}</strong>
        </div>

        <div className="rounded-xl border border-slate-200/80 bg-slate-50/70 p-2.5">
          <span className="block text-[10px] text-slate-500 uppercase font-semibold tracking-wider">{t('roaming_status')}</span>
          <strong className="mt-0.5 block text-slate-800">
            {modem.roaming_enabled ? t('roaming_allowed') : t('roaming_blocked')}
          </strong>
        </div>

        <div className="rounded-xl border border-slate-200/80 bg-slate-50/70 p-2.5">
          <span className="block text-[10px] text-slate-500 uppercase font-semibold tracking-wider">{t('emergency_fallback_mode')}</span>
          <strong className="mt-0.5 block text-blue-600 font-medium">
            {modem.emergency_fallback_only ? t('emergency_only_active') : t('cellular_primary_allowed')}
          </strong>
        </div>
      </div>
    </div>
  );
};
