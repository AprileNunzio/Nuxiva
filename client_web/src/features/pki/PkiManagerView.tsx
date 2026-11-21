import React, { useEffect, useState } from 'react';
import {
  ShieldCheck,
  Lock,
  Download,
  RefreshCw,
  Key,
  Globe,
  Radio,
  CheckCircle2,
  AlertCircle,
  Copy,
  Server,
} from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { downloadClientBundle, fetchPkiStatus, generateEnterpriseCertificate } from './pkiApi';
import { PkiStatus } from './types';

export const PkiManagerView: React.FC = () => {
  const { t } = useScopedI18n('features/pki');
  const [status, setStatus] = useState<PkiStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'ok' | 'err'; msg: string } | null>(null);

  const [includeTailscale, setIncludeTailscale] = useState(true);
  const [includeVpn, setIncludeVpn] = useState(true);
  const [includeLan, setIncludeLan] = useState(true);
  const [customDns, setCustomDns] = useState('');
  const [customIps, setCustomIps] = useState('');

  const [clientIdentity, setClientIdentity] = useState('operator-device');
  const [clientPassword, setClientPassword] = useState('');
  const [downloadingClient, setDownloadingClient] = useState(false);

  const loadStatus = async () => {
    try {
      setLoading(true);
      const data = await fetchPkiStatus();
      setStatus(data);
    } catch {
      setFeedback({ type: 'err', msg: t('error_msg') });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    setGenerating(true);
    setFeedback(null);
    try {
      const dnsList = customDns
        .split(',')
        .map(s => s.trim())
        .filter(Boolean);
      const ipList = customIps
        .split(',')
        .map(s => s.trim())
        .filter(Boolean);

      const updated = await generateEnterpriseCertificate({
        include_tailscale: includeTailscale,
        include_vpn: includeVpn,
        custom_dns: dnsList,
        custom_ips: ipList,
      });
      setStatus(updated);
      setFeedback({ type: 'ok', msg: t('success_msg') });
    } catch {
      setFeedback({ type: 'err', msg: t('error_msg') });
    } finally {
      setGenerating(false);
    }
  };

  const handleClientDownload = async (e: React.FormEvent) => {
    e.preventDefault();
    setDownloadingClient(true);
    try {
      await downloadClientBundle(clientIdentity, clientPassword || undefined);
    } catch {
      setFeedback({ type: 'err', msg: t('error_msg') });
    } finally {
      setDownloadingClient(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  if (loading && !status) {
    return (
      <div className="flex h-64 items-center justify-center">
        <RefreshCw className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="@container w-full space-y-6 p-4 sm:p-6 text-on-surface">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight sm:text-2xl">{t('title')}</h1>
          <p className="text-xs text-on-surface-variant sm:text-sm">{t('subtitle')}</p>
        </div>
        <button
          type="button"
          onClick={loadStatus}
          disabled={loading}
          className="inline-flex items-center gap-1.5 self-start rounded-xl border border-outline-variant bg-surface-container px-3 py-1.5 text-xs font-semibold hover:bg-surface-container-high transition"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Aggiorna</span>
        </button>
      </div>

      {feedback && (
        <div
          className={`flex items-center gap-2 rounded-xl border p-3 text-xs font-medium sm:text-sm ${
            feedback.type === 'ok'
              ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
              : 'border-rose-500/30 bg-rose-500/10 text-rose-400'
          }`}
        >
          {feedback.type === 'ok' ? (
            <CheckCircle2 className="h-4 w-4 shrink-0" />
          ) : (
            <AlertCircle className="h-4 w-4 shrink-0" />
          )}
          <span>{feedback.msg}</span>
        </div>
      )}

      <div className="grid gap-6 cq-md:grid-cols-2">
        <div className="flex flex-col justify-between rounded-2xl border border-outline-variant/60 bg-surface-container p-5 shadow-sm">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-primary">
                {t('ca_card_title')}
              </span>
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-400">
                <ShieldCheck className="h-3 w-3" />
                {t('ca_active')}
              </span>
            </div>
            <p className="text-sm font-semibold text-on-surface">{status?.ca_subject || 'Nuxiva Root CA'}</p>
            <div className="space-y-1">
              <span className="text-[11px] text-on-surface-variant">{t('ca_fingerprint')}</span>
              <div className="flex items-center justify-between rounded-lg bg-surface-container-high p-2 font-mono text-[11px]">
                <span className="truncate">{status?.ca_fingerprint}</span>
                <button
                  type="button"
                  onClick={() => status?.ca_fingerprint && copyToClipboard(status.ca_fingerprint)}
                  className="ml-2 text-on-surface-variant hover:text-on-surface"
                >
                  <Copy className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          </div>
          <div className="mt-4 flex flex-wrap gap-2 pt-2 border-t border-outline-variant/30">
            <a
              href="/nuxiva-ca.crt"
              download
              className="inline-flex items-center gap-1.5 rounded-xl border border-outline-variant bg-surface-container-high px-3 py-2 text-xs font-semibold hover:bg-surface-container-highest transition"
            >
              <Download className="h-3.5 w-3.5 text-primary" />
              {t('download_ca_crt')}
            </a>
            <a
              href="/nuxiva-ca.pem"
              download
              className="inline-flex items-center gap-1.5 rounded-xl border border-outline-variant bg-surface-container-high px-3 py-2 text-xs font-semibold hover:bg-surface-container-highest transition"
            >
              <Download className="h-3.5 w-3.5 text-primary" />
              {t('download_ca_pem')}
            </a>
          </div>
        </div>

        <div className="flex flex-col justify-between rounded-2xl border border-outline-variant/60 bg-surface-container p-5 shadow-sm">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-primary">
                {t('server_card_title')}
              </span>
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-400">
                <Lock className="h-3 w-3" />
                {t('server_active')}
              </span>
            </div>
            <div className="space-y-1">
              <span className="text-[11px] text-on-surface-variant">{t('server_expires')}</span>
              <p className="text-xs font-medium text-on-surface">
                {status?.server_expires_at ? new Date(status.server_expires_at).toLocaleString() : 'N/A'}
              </p>
            </div>
            <div className="space-y-1">
              <span className="text-[11px] text-on-surface-variant">Fingerprint SHA-256</span>
              <div className="flex items-center justify-between rounded-lg bg-surface-container-high p-2 font-mono text-[11px]">
                <span className="truncate">{status?.server_fingerprint}</span>
                <button
                  type="button"
                  onClick={() => status?.server_fingerprint && copyToClipboard(status.server_fingerprint)}
                  className="ml-2 text-on-surface-variant hover:text-on-surface"
                >
                  <Copy className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          </div>
          <div className="mt-4 flex flex-wrap gap-2 pt-2 border-t border-outline-variant/30 text-xs">
            {status?.tailscale_detected && (
              <span className="inline-flex items-center gap-1 rounded-lg bg-sky-500/15 px-2.5 py-1 text-sky-400 font-semibold text-[11px]">
                <Globe className="h-3 w-3" />
                {t('tailscale_detected')}
              </span>
            )}
            {status?.vpn_detected && (
              <span className="inline-flex items-center gap-1 rounded-lg bg-indigo-500/15 px-2.5 py-1 text-indigo-400 font-semibold text-[11px]">
                <Radio className="h-3 w-3" />
                {t('vpn_detected')}
              </span>
            )}
            <span className="inline-flex items-center gap-1 rounded-lg bg-primary/15 px-2.5 py-1 text-primary font-semibold text-[11px]">
              <Server className="h-3 w-3" />
              {t('lan_detected')}
            </span>
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-outline-variant/60 bg-surface-container p-5 shadow-sm space-y-4">
        <h3 className="text-sm font-bold text-on-surface">{t('sans_title')}</h3>
        <div className="flex flex-wrap gap-2">
          {status?.sans.map((s, idx) => {
            const badgeColor =
              s.category === 'tailscale'
                ? 'bg-sky-500/15 text-sky-400 border-sky-500/30'
                : s.category === 'vpn'
                ? 'bg-indigo-500/15 text-indigo-400 border-indigo-500/30'
                : s.category === 'loopback'
                ? 'bg-surface-container-high text-on-surface-variant border-outline-variant/40'
                : 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30';
            return (
              <span
                key={idx}
                className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-mono font-medium ${badgeColor}`}
              >
                {s.kind === 'ip' ? <Radio className="h-3 w-3" /> : <Globe className="h-3 w-3" />}
                <span>{s.value}</span>
              </span>
            );
          })}
        </div>
      </div>

      <div className="grid gap-6 cq-md:grid-cols-2">
        <form
          onSubmit={handleGenerate}
          className="rounded-2xl border border-outline-variant/60 bg-surface-container p-5 shadow-sm space-y-4"
        >
          <h3 className="text-sm font-bold text-on-surface">{t('configure_title')}</h3>
          <div className="space-y-2 text-xs">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={includeTailscale}
                onChange={e => setIncludeTailscale(e.target.checked)}
                className="rounded border-outline-variant text-primary focus:ring-primary"
              />
              <span>{t('opt_tailscale')}</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={includeVpn}
                onChange={e => setIncludeVpn(e.target.checked)}
                className="rounded border-outline-variant text-primary focus:ring-primary"
              />
              <span>{t('opt_vpn')}</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={includeLan}
                onChange={e => setIncludeLan(e.target.checked)}
                className="rounded border-outline-variant text-primary focus:ring-primary"
              />
              <span>{t('opt_lan')}</span>
            </label>
          </div>
          <div className="space-y-1">
            <label className="text-xs text-on-surface-variant">{t('custom_dns_label')}</label>
            <input
              type="text"
              value={customDns}
              onChange={e => setCustomDns(e.target.value)}
              placeholder="sub.mydomain.com, myhost.ts.net"
              className="w-full rounded-xl border border-outline-variant bg-surface px-3 py-2 text-xs text-on-surface focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-on-surface-variant">{t('custom_ips_label')}</label>
            <input
              type="text"
              value={customIps}
              onChange={e => setCustomIps(e.target.value)}
              placeholder="10.8.0.1, 100.64.0.1"
              className="w-full rounded-xl border border-outline-variant bg-surface px-3 py-2 text-xs text-on-surface focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
          <button
            type="submit"
            disabled={generating}
            className="w-full rounded-xl bg-primary px-4 py-2.5 text-xs font-bold text-on-primary shadow-xs transition hover:opacity-95 disabled:opacity-50"
          >
            {generating ? t('btn_generating') : t('btn_generate')}
          </button>
        </form>

        <form
          onSubmit={handleClientDownload}
          className="rounded-2xl border border-outline-variant/60 bg-surface-container p-5 shadow-sm space-y-4"
        >
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-on-surface">{t('client_title')}</h3>
            <Key className="h-4 w-4 text-primary" />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-on-surface-variant">{t('client_identity_label')}</label>
            <input
              type="text"
              value={clientIdentity}
              onChange={e => setClientIdentity(e.target.value)}
              required
              className="w-full rounded-xl border border-outline-variant bg-surface px-3 py-2 text-xs text-on-surface focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-on-surface-variant">{t('client_password_label')}</label>
            <input
              type="password"
              value={clientPassword}
              onChange={e => setClientPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full rounded-xl border border-outline-variant bg-surface px-3 py-2 text-xs text-on-surface focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
          <button
            type="submit"
            disabled={downloadingClient}
            className="w-full rounded-xl border border-outline-variant bg-surface-container-high px-4 py-2.5 text-xs font-bold text-on-surface transition hover:bg-surface-container-highest disabled:opacity-50"
          >
            {downloadingClient ? 'Generazione...' : t('btn_download_client')}
          </button>
        </form>
      </div>
    </div>
  );
};
