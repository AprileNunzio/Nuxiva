import React from 'react';
import { AlertCircle, Radio, Signal, SignalHigh, SignalLow, SignalMedium, SignalZero } from 'lucide-react';
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
      <div className="rounded-2xl border border-slate-800/60 bg-slate-950/40 p-4 sm:p-5 flex items-center gap-3 text-slate-500">
        <Radio className="h-5 w-5" />
        <span className="text-xs">{t('no_gsm_modem_detected')}</span>
      </div>
    );
  }

  const SignalIcon = getSignalIcon(modem.signal_bars);

  return (
    <div className="rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900/60 to-slate-950/90 p-4 sm:p-5">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-purple-400/40 bg-purple-400/10 text-purple-300">
            <Radio className="h-5 w-5" />
          </span>
          <div>
            <div className="flex items-center gap-2">
              <strong className="text-sm font-semibold text-white">{t('gsm_modem_title')}</strong>
              <span className="rounded-full border border-purple-400/40 bg-purple-400/10 px-2 py-0.5 font-mono text-[9px] uppercase font-bold text-purple-300">
                {modem.technology}
              </span>
              <span
                className={`rounded-full border px-2 py-0.5 font-mono text-[9px] uppercase ${
                  modem.is_connected
                    ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
                    : 'border-amber-500/40 bg-amber-500/10 text-amber-300'
                }`}
              >
                {modem.is_connected ? t('gsm_connected') : t('gsm_standby')}
              </span>
            </div>
            <span className="text-xs text-slate-400">{modem.operator}</span>
          </div>
        </div>

        <div className="flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-900/80 px-2.5 py-1 text-xs">
          <SignalIcon className={`h-4 w-4 ${modem.signal_bars >= 3 ? 'text-emerald-400' : 'text-amber-400'}`} />
          <span className="font-mono text-slate-200">{modem.signal_dbm} dBm</span>
          <span className="text-slate-400 font-mono text-[10px]">({modem.signal_bars}/5)</span>
        </div>
      </div>

      <div className="grid gap-2 sm:grid-cols-3 text-xs">
        <div className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-2.5">
          <span className="block text-[10px] text-slate-400 uppercase tracking-wider">{t('gsm_apn')}</span>
          <strong className="mt-0.5 block font-mono text-slate-200">{modem.apn}</strong>
        </div>

        <div className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-2.5">
          <span className="block text-[10px] text-slate-400 uppercase tracking-wider">{t('roaming_status')}</span>
          <strong className="mt-0.5 block text-slate-200">
            {modem.roaming_enabled ? t('roaming_allowed') : t('roaming_blocked')}
          </strong>
        </div>

        <div className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-2.5">
          <span className="block text-[10px] text-slate-400 uppercase tracking-wider">{t('emergency_fallback_mode')}</span>
          <strong className="mt-0.5 block text-cyan-300">
            {modem.emergency_fallback_only ? t('emergency_only_active') : t('cellular_primary_allowed')}
          </strong>
        </div>
      </div>

      {modem.emergency_fallback_only && (
        <div className="mt-3 flex items-center gap-2 rounded-xl border border-purple-500/30 bg-purple-950/20 px-3 py-2 text-[11px] text-purple-200">
          <AlertCircle className="h-3.5 w-3.5 shrink-0 text-purple-400" />
          <span>{t('emergency_mode_notice')}</span>
        </div>
      )}
    </div>
  );
};
