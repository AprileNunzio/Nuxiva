import React, { useState } from 'react';
import { AlertCircle, Check, X } from 'lucide-react';
import { IpAssignmentMode, IpConfigPayload, NetworkInterface } from '../types';

interface IpConfigModalProps {
  readonly iface: NetworkInterface;
  readonly isOpen: boolean;
  readonly saving: boolean;
  readonly onClose: () => void;
  readonly onSave: (config: IpConfigPayload) => void;
  readonly t: (key: string) => string;
}

function isValidIpv4(ip: string): boolean {
  const parts = ip.trim().split('.');
  if (parts.length !== 4) return false;
  return parts.every((p) => {
    if (!/^\d{1,3}$/.test(p)) return false;
    const num = Number(p);
    return num >= 0 && num <= 255;
  });
}

export const IpConfigModal: React.FC<IpConfigModalProps> = ({
  iface,
  isOpen,
  saving,
  onClose,
  onSave,
  t,
}) => {
  const [mode, setMode] = useState<IpAssignmentMode>(iface.ip_mode);
  const [ipv4, setIpv4] = useState(iface.ipv4 || '');
  const [netmask, setNetmask] = useState(iface.netmask || '255.255.255.0');
  const [gateway, setGateway] = useState(iface.gateway || '');
  const [dnsPrimary, setDnsPrimary] = useState(iface.dns_primary || '1.1.1.1');
  const [dnsSecondary, setDnsSecondary] = useState(iface.dns_secondary || '8.8.8.8');
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSave = () => {
    setError(null);
    if (mode === 'static') {
      if (!isValidIpv4(ipv4)) {
        setError(t('error_invalid_ipv4'));
        return;
      }
      if (!isValidIpv4(netmask)) {
        setError(t('error_invalid_netmask'));
        return;
      }
      if (gateway && !isValidIpv4(gateway)) {
        setError(t('error_invalid_gateway'));
        return;
      }
      if (dnsPrimary && !isValidIpv4(dnsPrimary)) {
        setError(t('error_invalid_dns'));
        return;
      }
      if (dnsSecondary && !isValidIpv4(dnsSecondary)) {
        setError(t('error_invalid_dns'));
        return;
      }
    }

    onSave({
      mode,
      ipv4: mode === 'static' ? ipv4 : null,
      netmask: mode === 'static' ? netmask : null,
      gateway: mode === 'static' ? gateway : null,
      dns_primary: mode === 'static' ? dnsPrimary : null,
      dns_secondary: mode === 'static' ? dnsSecondary : null,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
          <div>
            <h3 className="text-lg font-bold text-slate-900">
              {t('ip_modal_title')} — <span className="font-mono text-blue-600">{iface.name}</span>
            </h3>
            <p className="text-xs text-slate-500">{iface.mac_address}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700 transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {error && (
          <div className="mb-4 flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-700">
            <AlertCircle className="h-4 w-4 shrink-0 text-rose-500" />
            <span>{error}</span>
          </div>
        )}

        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">
              {t('ip_assignment_mode')}
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setMode('dhcp')}
                className={`rounded-xl border p-3 text-left transition ${
                  mode === 'dhcp'
                    ? 'border-blue-500 bg-blue-50/70 text-slate-900 ring-2 ring-blue-500/20 shadow-xs'
                    : 'border-slate-200 bg-slate-50/60 text-slate-600 hover:border-slate-300'
                }`}
              >
                <strong className="block text-sm font-semibold text-slate-900">DHCP</strong>
                <span className="text-[11px] text-slate-500">{t('dhcp_desc')}</span>
              </button>

              <button
                type="button"
                onClick={() => setMode('static')}
                className={`rounded-xl border p-3 text-left transition ${
                  mode === 'static'
                    ? 'border-blue-500 bg-blue-50/70 text-slate-900 ring-2 ring-blue-500/20 shadow-xs'
                    : 'border-slate-200 bg-slate-50/60 text-slate-600 hover:border-slate-300'
                }`}
              >
                <strong className="block text-sm font-semibold text-slate-900">{t('static_ip')}</strong>
                <span className="text-[11px] text-slate-500">{t('static_ip_desc')}</span>
              </button>
            </div>
          </div>

          {mode === 'static' && (
            <div className="space-y-3 pt-2 border-t border-slate-100">
              <div>
                <label className="block text-xs text-slate-600 font-medium mb-1">{t('ip_address')} *</label>
                <input
                  type="text"
                  value={ipv4}
                  onChange={(e) => setIpv4(e.target.value)}
                  placeholder="192.168.1.150"
                  className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 font-mono text-sm text-slate-900 focus:border-blue-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-slate-600 font-medium mb-1">{t('netmask')} *</label>
                  <input
                    type="text"
                    value={netmask}
                    onChange={(e) => setNetmask(e.target.value)}
                    placeholder="255.255.255.0"
                    className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 font-mono text-sm text-slate-900 focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-600 font-medium mb-1">{t('gateway')}</label>
                  <input
                    type="text"
                    value={gateway}
                    onChange={(e) => setGateway(e.target.value)}
                    placeholder="192.168.1.1"
                    className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 font-mono text-sm text-slate-900 focus:border-blue-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-slate-600 font-medium mb-1">{t('dns_primary')}</label>
                  <input
                    type="text"
                    value={dnsPrimary}
                    onChange={(e) => setDnsPrimary(e.target.value)}
                    placeholder="1.1.1.1"
                    className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 font-mono text-sm text-slate-900 focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-600 font-medium mb-1">{t('dns_secondary')}</label>
                  <input
                    type="text"
                    value={dnsSecondary}
                    onChange={(e) => setDnsSecondary(e.target.value)}
                    placeholder="8.8.8.8"
                    className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 font-mono text-sm text-slate-900 focus:border-blue-500 focus:outline-none"
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="mt-6 flex justify-end gap-3 border-t border-slate-100 pt-4">
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 transition"
          >
            {t('cancel')}
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-1.5 rounded-xl border border-blue-600 bg-blue-600 px-5 py-2 text-xs font-semibold text-white hover:bg-blue-700 transition shadow-sm disabled:opacity-50"
          >
            <Check className="h-4 w-4" />
            {saving ? `${t('saving')}...` : t('save')}
          </button>
        </div>
      </div>
    </div>
  );
};
