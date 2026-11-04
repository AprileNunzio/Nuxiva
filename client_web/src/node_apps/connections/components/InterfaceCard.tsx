import React from 'react';
import { Cable, Cpu, Edit, Radio, Shield, ToggleLeft, ToggleRight, Wifi } from 'lucide-react';
import { InterfaceKind, NetworkInterface } from '../types';

interface InterfaceCardProps {
  readonly iface: NetworkInterface;
  readonly isPrimary: boolean;
  readonly isSecondary: boolean;
  readonly onToggle: (name: string, nextUp: boolean) => void;
  readonly onEditIp: (iface: NetworkInterface) => void;
  readonly t: (key: string) => string;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  const mb = kb / 1024;
  if (mb < 1024) return `${mb.toFixed(1)} MB`;
  const gb = mb / 1024;
  return `${gb.toFixed(2)} GB`;
}

function getInterfaceIcon(kind: InterfaceKind) {
  switch (kind) {
    case 'ethernet':
      return Cable;
    case 'wifi':
      return Wifi;
    case 'cellular_gsm':
      return Radio;
    case 'vpn':
      return Shield;
    default:
      return Cpu;
  }
}

export const InterfaceCard: React.FC<InterfaceCardProps> = ({
  iface,
  isPrimary,
  isSecondary,
  onToggle,
  onEditIp,
  t,
}) => {
  const Icon = getInterfaceIcon(iface.kind);

  return (
    <div
      className={`rounded-2xl border p-4 sm:p-5 transition flex flex-col justify-between gap-4 shadow-2xs ${
        iface.is_up
          ? isPrimary
            ? 'border-blue-400 bg-blue-50/40 ring-1 ring-blue-300 shadow-xs'
            : isSecondary
            ? 'border-emerald-400 bg-emerald-50/40 ring-1 ring-emerald-300 shadow-xs'
            : 'border-slate-200/90 bg-white'
          : 'border-slate-200/80 bg-slate-50/70 opacity-60'
      }`}
    >
      <div>
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-3">
            <span
              className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border ${
                iface.is_up
                  ? 'border-blue-200 bg-blue-50 text-blue-600'
                  : 'border-slate-200 bg-slate-100 text-slate-400'
              }`}
            >
              <Icon className="h-5 w-5" />
            </span>
            <div>
              <div className="flex items-center gap-2">
                <strong className="font-mono text-base font-bold text-slate-900">{iface.name}</strong>
                <span className="rounded-full border border-slate-200 bg-slate-100 px-2 py-0.5 font-mono text-[10px] uppercase text-slate-600 font-semibold">
                  {t(`kind_${iface.kind}`)}
                </span>
                {isPrimary && (
                  <span className="rounded-full border border-blue-200 bg-blue-100 px-2 py-0.5 font-mono text-[9px] uppercase font-bold text-blue-700">
                    {t('role_primary')}
                  </span>
                )}
                {isSecondary && (
                  <span className="rounded-full border border-emerald-200 bg-emerald-100 px-2 py-0.5 font-mono text-[9px] uppercase font-bold text-emerald-700">
                    {t('role_secondary')}
                  </span>
                )}
              </div>
              <span className="font-mono text-[11px] text-slate-500">{iface.mac_address}</span>
            </div>
          </div>

          <button
            type="button"
            onClick={() => onToggle(iface.name, !iface.is_up)}
            className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-100 transition"
            title={iface.is_up ? t('turn_off') : t('turn_on')}
          >
            {iface.is_up ? (
              <>
                <ToggleRight className="h-4 w-4 text-emerald-600" />
                <span className="text-emerald-700 font-semibold">{t('interface_up')}</span>
              </>
            ) : (
              <>
                <ToggleLeft className="h-4 w-4 text-slate-400" />
                <span className="text-slate-500">{t('interface_down')}</span>
              </>
            )}
          </button>
        </div>

        <div className="grid gap-2 sm:grid-cols-2 text-xs">
          <div className="rounded-xl border border-slate-200/80 bg-slate-50/70 p-2.5">
            <span className="block text-[10px] text-slate-500 uppercase font-semibold tracking-wider">{t('ip_address')}</span>
            <div className="mt-0.5 flex items-center justify-between">
              <strong className="font-mono text-blue-600 font-bold">{iface.ipv4 || t('not_assigned')}</strong>
              <span className="rounded-full border border-slate-200 bg-white px-1.5 py-0.2 font-mono text-[9px] uppercase text-slate-600 font-semibold">
                {iface.ip_mode.toUpperCase()}
              </span>
            </div>
          </div>

          <div className="rounded-xl border border-slate-200/80 bg-slate-50/70 p-2.5">
            <span className="block text-[10px] text-slate-500 uppercase font-semibold tracking-wider">{t('gateway')}</span>
            <strong className="mt-0.5 block font-mono text-slate-800">{iface.gateway || '—'}</strong>
          </div>

          <div className="rounded-xl border border-slate-200/80 bg-slate-50/70 p-2.5">
            <span className="block text-[10px] text-slate-500 uppercase font-semibold tracking-wider">{t('netmask')}</span>
            <strong className="mt-0.5 block font-mono text-slate-800">{iface.netmask || '—'}</strong>
          </div>

          <div className="rounded-xl border border-slate-200/80 bg-slate-50/70 p-2.5">
            <span className="block text-[10px] text-slate-500 uppercase font-semibold tracking-wider">{t('dns')}</span>
            <strong className="mt-0.5 block font-mono text-slate-800 truncate">
              {iface.dns_primary ? `${iface.dns_primary}${iface.dns_secondary ? `, ${iface.dns_secondary}` : ''}` : '—'}
            </strong>
          </div>
        </div>

        <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-slate-200/80 pt-3 text-[11px] text-slate-500 font-mono">
          <div className="flex gap-3">
            {iface.speed_mbps != null && <span>{iface.speed_mbps} Mbps</span>}
            <span>MTU {iface.mtu}</span>
            {iface.signal_percent != null && (
              <span className="text-emerald-600 font-bold">{iface.signal_percent}% {t('signal')}</span>
            )}
          </div>
          <div className="flex gap-3">
            <span>RX: {formatBytes(iface.rx_bytes)}</span>
            <span>TX: {formatBytes(iface.tx_bytes)}</span>
          </div>
        </div>
      </div>

      <div className="flex justify-end pt-2 border-t border-slate-100">
        <button
          type="button"
          onClick={() => onEditIp(iface)}
          className="flex items-center gap-1.5 rounded-lg border border-blue-200 bg-blue-50/80 px-3 py-1.5 text-xs font-semibold text-blue-700 hover:bg-blue-100 hover:border-blue-300 transition"
        >
          <Edit className="h-3.5 w-3.5" />
          {t('configure_ip_action')}
        </button>
      </div>
    </div>
  );
};
