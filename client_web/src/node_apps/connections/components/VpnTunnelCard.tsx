import React from 'react';
import { Lock, Shield, ShieldAlert, ToggleLeft, ToggleRight } from 'lucide-react';
import { VpnTunnel } from '../types';

interface VpnTunnelCardProps {
  readonly vpn: VpnTunnel;
  readonly toggling: boolean;
  readonly onToggleVpn: (enabled: boolean) => void;
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

export const VpnTunnelCard: React.FC<VpnTunnelCardProps> = ({ vpn, toggling, onToggleVpn, t }) => (
  <div className="rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900/60 to-slate-950/90 p-4 sm:p-5">
    <div className="flex items-start justify-between gap-3 mb-3">
      <div className="flex items-center gap-3">
        <span
          className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border ${
            vpn.enabled
              ? 'border-emerald-400/40 bg-emerald-400/10 text-emerald-300'
              : 'border-slate-700 bg-slate-800/80 text-slate-500'
          }`}
        >
          {vpn.enabled ? <Shield className="h-5 w-5" /> : <ShieldAlert className="h-5 w-5" />}
        </span>
        <div>
          <div className="flex items-center gap-2">
            <strong className="text-sm font-semibold text-white">{t('vpn_tunnel_title')}</strong>
            <span className="font-mono text-xs text-cyan-300">({vpn.tunnel_name})</span>
            <span
              className={`rounded-full border px-2 py-0.5 font-mono text-[9px] uppercase ${
                vpn.enabled
                  ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
                  : 'border-slate-700 bg-slate-800 text-slate-400'
              }`}
            >
              {vpn.enabled ? t('vpn_active') : t('vpn_disabled')}
            </span>
          </div>
          <span className="text-xs text-slate-400">{t('wireguard_mesh_desc')}</span>
        </div>
      </div>

      <button
        type="button"
        disabled={toggling}
        onClick={() => onToggleVpn(!vpn.enabled)}
        className="flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-900/80 px-2.5 py-1 text-xs font-medium text-slate-300 hover:border-slate-600 transition disabled:opacity-50"
      >
        {vpn.enabled ? (
          <>
            <ToggleRight className="h-4 w-4 text-emerald-400" />
            <span className="text-emerald-400 font-semibold">{t('vpn_enabled_label')}</span>
          </>
        ) : (
          <>
            <ToggleLeft className="h-4 w-4 text-slate-500" />
            <span className="text-slate-400">{t('vpn_disabled_label')}</span>
          </>
        )}
      </button>
    </div>

    <div className="grid gap-2 sm:grid-cols-3 text-xs">
      <div className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-2.5">
        <span className="block text-[10px] text-slate-400 uppercase tracking-wider">{t('mesh_virtual_ip')}</span>
        <strong className="mt-0.5 block font-mono text-cyan-200">{vpn.virtual_ip}</strong>
      </div>

      <div className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-2.5">
        <span className="block text-[10px] text-slate-400 uppercase tracking-wider">{t('vpn_endpoint')}</span>
        <strong className="mt-0.5 block font-mono text-slate-200 truncate">{vpn.endpoint}</strong>
      </div>

      <div className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-2.5">
        <span className="block text-[10px] text-slate-400 uppercase tracking-wider">{t('encrypted_traffic')}</span>
        <strong className="mt-0.5 block font-mono text-slate-200">{formatBytes(vpn.bytes_transferred)}</strong>
      </div>
    </div>

    {vpn.enabled && (
      <div className="mt-3 flex items-center justify-between border-t border-slate-800/60 pt-3 text-[11px] text-slate-400">
        <div className="flex items-center gap-1.5 text-emerald-400">
          <Lock className="h-3.5 w-3.5" />
          <span>{t('e2e_mesh_encrypted')}</span>
        </div>
        {vpn.handshake_age_secs != null && (
          <span className="font-mono text-slate-400">
            {t('last_handshake')}: {vpn.handshake_age_secs}s fa
          </span>
        )}
      </div>
    )}
  </div>
);
