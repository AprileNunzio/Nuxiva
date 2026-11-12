import React from 'react';
import { Lock, Shield, ShieldAlert, ToggleLeft, ToggleRight } from 'lucide-react';
import { VpnTunnel } from '../types';

interface VpnTunnelCardProps {
  readonly vpn: VpnTunnel | null;
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

export const VpnTunnelCard: React.FC<VpnTunnelCardProps> = ({ vpn, toggling, onToggleVpn, t }) => {
  if (!vpn || !vpn.tunnel_name) {
    return (
      <div className="rounded-2xl border border-slate-200/90 bg-white p-5 flex items-center gap-3 text-slate-600 shadow-2xs">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-slate-100 text-slate-400">
          <ShieldAlert className="h-5 w-5" />
        </div>
        <div className="flex flex-col">
          <strong className="text-sm font-semibold text-slate-800">{t('vpn_tunnel_title')}</strong>
          <span className="text-xs text-slate-500">{t('no_vpn_tunnel_configured')}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-slate-200/90 bg-white p-4 sm:p-5 shadow-2xs">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-3">
          <span
            className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border ${
              vpn.enabled
                ? 'border-emerald-200 bg-emerald-50 text-emerald-600'
                : 'border-slate-200 bg-slate-100 text-slate-400'
            }`}
          >
            {vpn.enabled ? <Shield className="h-5 w-5" /> : <ShieldAlert className="h-5 w-5" />}
          </span>
          <div>
            <div className="flex items-center gap-2">
              <strong className="text-sm font-semibold text-slate-900">{t('vpn_tunnel_title')}</strong>
              <span className="font-mono text-xs text-blue-600 font-semibold">({vpn.tunnel_name})</span>
              <span
                className={`rounded-full border px-2 py-0.5 font-mono text-[9px] uppercase font-semibold ${
                  vpn.enabled
                    ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                    : 'border-slate-200 bg-slate-100 text-slate-500'
                }`}
              >
                {vpn.enabled ? t('vpn_active') : t('vpn_disabled')}
              </span>
            </div>
            <span className="text-xs text-slate-500">{t('wireguard_mesh_desc')}</span>
          </div>
        </div>

        <button
          type="button"
          disabled={toggling}
          onClick={() => onToggleVpn(!vpn.enabled)}
          className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-100 transition disabled:opacity-50"
        >
          {vpn.enabled ? (
            <>
              <ToggleRight className="h-4 w-4 text-emerald-600" />
              <span className="text-emerald-700 font-semibold">{t('vpn_enabled_label')}</span>
            </>
          ) : (
            <>
              <ToggleLeft className="h-4 w-4 text-slate-400" />
              <span className="text-slate-500">{t('vpn_disabled_label')}</span>
            </>
          )}
        </button>
      </div>

      <div className="grid gap-2 sm:grid-cols-3 text-xs">
        <div className="rounded-xl border border-slate-200/80 bg-slate-50/70 p-2.5">
          <span className="block text-[10px] text-slate-500 uppercase font-semibold tracking-wider">{t('mesh_virtual_ip')}</span>
          <strong className="mt-0.5 block font-mono text-blue-600 font-bold">{vpn.virtual_ip}</strong>
        </div>

        <div className="rounded-xl border border-slate-200/80 bg-slate-50/70 p-2.5">
          <span className="block text-[10px] text-slate-500 uppercase font-semibold tracking-wider">{t('vpn_endpoint')}</span>
          <strong className="mt-0.5 block font-mono text-slate-800 truncate">{vpn.endpoint}</strong>
        </div>

        <div className="rounded-xl border border-slate-200/80 bg-slate-50/70 p-2.5">
          <span className="block text-[10px] text-slate-500 uppercase font-semibold tracking-wider">{t('encrypted_traffic')}</span>
          <strong className="mt-0.5 block font-mono text-slate-800">{formatBytes(vpn.bytes_transferred)}</strong>
        </div>
      </div>

      {vpn.enabled && (
        <div className="mt-3 flex items-center justify-between border-t border-slate-200/80 pt-3 text-[11px] text-slate-500">
          <div className="flex items-center gap-1.5 text-emerald-600 font-medium">
            <Lock className="h-3.5 w-3.5" />
            <span>{t('e2e_mesh_encrypted')}</span>
          </div>
          {vpn.handshake_age_secs != null && (
            <span className="font-mono text-slate-500">
              {t('last_handshake')}: {vpn.handshake_age_secs}s fa
            </span>
          )}
        </div>
      )}
    </div>
  );
};
