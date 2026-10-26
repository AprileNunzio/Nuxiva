import React, { useState } from 'react';
import { Eye, EyeOff, KeyRound, Loader2, Lock, Radio, RefreshCw, Signal, Unlock, Wifi, WifiOff } from 'lucide-react';
import { WifiConnectPayload, WifiNetwork, WifiScanResult } from '../types';

interface WifiScannerProps {
  readonly scanResult: WifiScanResult | null;
  readonly scanning: boolean;
  readonly connecting: boolean;
  readonly onRescan: () => void;
  readonly onConnect: (payload: WifiConnectPayload) => Promise<void>;
  readonly onDisconnect: () => Promise<void>;
  readonly onToggleRadio: (enabled: boolean) => Promise<void>;
  readonly t: (key: string) => string;
}

export const WifiScanner: React.FC<WifiScannerProps> = ({
  scanResult,
  scanning,
  connecting,
  onRescan,
  onConnect,
  onDisconnect,
  onToggleRadio,
  t,
}) => {
  const [selectedSsid, setSelectedSsid] = useState<string | null>(null);
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [manualMode, setManualMode] = useState(false);
  const [manualSsid, setManualSsid] = useState('');

  const networks = scanResult?.networks || [];
  const radioEnabled = scanResult?.radio_enabled ?? true;
  const currentSsid = scanResult?.current_ssid;

  const handleStartConnect = (ssid: string) => {
    setSelectedSsid(ssid);
    setPassword('');
    setShowPassword(false);
  };

  const handleSubmitConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    const ssidToConnect = manualMode ? manualSsid.trim() : selectedSsid;
    if (!ssidToConnect) return;
    await onConnect({
      ssid: ssidToConnect,
      password: password.trim(),
      interface: scanResult?.interface,
    });
    setSelectedSsid(null);
    setPassword('');
    setManualMode(false);
  };

  const renderSignalBars = (pct: number) => {
    const bars = pct >= 80 ? 4 : pct >= 55 ? 3 : pct >= 30 ? 2 : 1;
    return (
      <div className="flex items-end gap-0.5 h-4">
        {[1, 2, 3, 4].map((bar) => (
          <div
            key={bar}
            style={{ height: `${bar * 25}%` }}
            className={`w-1 rounded-xs transition-colors ${
              bar <= bars
                ? pct >= 70
                  ? 'bg-emerald-400 shadow-xs shadow-emerald-400/50'
                  : pct >= 40
                  ? 'bg-cyan-400 shadow-xs shadow-cyan-400/50'
                  : 'bg-amber-400 shadow-xs shadow-amber-400/50'
                : 'bg-slate-700/60'
            }`}
          />
        ))}
      </div>
    );
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md p-4">
        <div className="flex items-center gap-3">
          <span
            className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border ${
              radioEnabled
                ? 'border-cyan-400/40 bg-cyan-400/10 text-cyan-300'
                : 'border-rose-400/40 bg-rose-400/10 text-rose-400'
            }`}
          >
            {radioEnabled ? <Wifi className="h-6 w-6" /> : <WifiOff className="h-6 w-6" />}
          </span>
          <div>
            <div className="flex items-center gap-2">
              <strong className="text-sm font-semibold text-white">
                {t('wifi_adapter')}: {scanResult?.interface || 'Wi-Fi'}
              </strong>
              <span
                className={`rounded-full px-2 py-0.5 text-[10px] font-mono font-bold uppercase ${
                  radioEnabled
                    ? 'border border-emerald-400/40 bg-emerald-400/10 text-emerald-300'
                    : 'border border-rose-400/40 bg-rose-400/10 text-rose-400'
                }`}
              >
                {radioEnabled ? t('wifi_radio_on') : t('wifi_radio_off')}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              {currentSsid ? `${t('wifi_currently_connected')}: ${currentSsid}` : t('wifi_not_connected')}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 self-end sm:self-center">
          <button
            type="button"
            onClick={() => void onToggleRadio(!radioEnabled)}
            className={`rounded-xl border px-3 py-1.5 text-xs font-semibold transition ${
              radioEnabled
                ? 'border-slate-700 bg-slate-800 text-slate-300 hover:border-slate-600 hover:text-white'
                : 'border-emerald-500/50 bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30'
            }`}
          >
            {radioEnabled ? t('wifi_turn_off_radio') : t('wifi_turn_on_radio')}
          </button>
          <button
            type="button"
            onClick={onRescan}
            disabled={scanning || !radioEnabled}
            className="flex items-center gap-1.5 rounded-xl border border-cyan-400/40 bg-cyan-400/10 px-3 py-1.5 text-xs font-semibold text-cyan-300 hover:bg-cyan-400/20 transition disabled:opacity-40"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${scanning ? 'animate-spin text-cyan-300' : ''}`} />
            {scanning ? t('scanning') : t('wifi_scan_action')}
          </button>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
          {t('wifi_detected_networks')} ({networks.length})
        </h3>
        <button
          type="button"
          onClick={() => {
            setManualMode(true);
            setSelectedSsid(null);
          }}
          className="text-xs font-semibold text-cyan-400 hover:text-cyan-300 transition"
        >
          + {t('wifi_add_hidden_network')}
        </button>
      </div>

      {manualMode && (
        <form
          onSubmit={handleSubmitConnect}
          className="rounded-2xl border border-cyan-400/40 bg-slate-900/90 p-4 sm:p-5 flex flex-col gap-3"
        >
          <div className="flex items-center justify-between">
            <strong className="text-sm font-semibold text-white">{t('wifi_connect_hidden')}</strong>
            <button
              type="button"
              onClick={() => setManualMode(false)}
              className="text-xs text-slate-400 hover:text-white transition"
            >
              {t('cancel')}
            </button>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="text-[11px] font-mono uppercase text-slate-400 block mb-1">SSID</label>
              <input
                type="text"
                value={manualSsid}
                onChange={(e) => setManualSsid(e.target.value)}
                placeholder="Nome della rete..."
                required
                className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white placeholder-slate-500 focus:border-cyan-400 focus:outline-hidden"
              />
            </div>
            <div>
              <label className="text-[11px] font-mono uppercase text-slate-400 block mb-1">{t('password')}</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Password di rete..."
                  className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 pr-9 text-xs text-white placeholder-slate-500 focus:border-cyan-400 focus:outline-hidden"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-2.5 top-2.5 text-slate-400 hover:text-white"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>
          </div>
          <div className="flex justify-end gap-2 mt-1">
            <button
              type="button"
              onClick={() => setManualMode(false)}
              className="rounded-xl border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-300"
            >
              {t('cancel')}
            </button>
            <button
              type="submit"
              disabled={connecting || !manualSsid.trim()}
              className="rounded-xl border border-cyan-400/50 bg-cyan-400/20 px-4 py-1.5 text-xs font-semibold text-cyan-200 hover:bg-cyan-400/30 transition disabled:opacity-40"
            >
              {connecting ? t('connecting') : t('wifi_connect_btn')}
            </button>
          </div>
        </form>
      )}

      {selectedSsid && (
        <form
          onSubmit={handleSubmitConnect}
          className="rounded-2xl border border-cyan-400/40 bg-slate-900/90 p-4 sm:p-5 flex flex-col gap-3"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <KeyRound className="h-4 w-4 text-cyan-400" />
              <strong className="text-sm font-semibold text-white">
                {t('wifi_connect_to')} <span className="text-cyan-300">{selectedSsid}</span>
              </strong>
            </div>
            <button
              type="button"
              onClick={() => setSelectedSsid(null)}
              className="text-xs text-slate-400 hover:text-white transition"
            >
              {t('cancel')}
            </button>
          </div>

          <div>
            <label className="text-[11px] font-mono uppercase text-slate-400 block mb-1">{t('password')}</label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password di rete Wi-Fi (lascia vuoto se aperta)..."
                autoFocus
                className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 pr-9 text-xs text-white placeholder-slate-500 focus:border-cyan-400 focus:outline-hidden"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-2.5 top-2.5 text-slate-400 hover:text-white"
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          <div className="flex justify-end gap-2 mt-1">
            <button
              type="button"
              onClick={() => setSelectedSsid(null)}
              className="rounded-xl border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-300"
            >
              {t('cancel')}
            </button>
            <button
              type="submit"
              disabled={connecting}
              className="flex items-center gap-1.5 rounded-xl border border-cyan-400/50 bg-cyan-400/20 px-4 py-1.5 text-xs font-semibold text-cyan-200 hover:bg-cyan-400/30 transition disabled:opacity-40"
            >
              {connecting && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              {connecting ? t('connecting') : t('wifi_connect_btn')}
            </button>
          </div>
        </form>
      )}

      {scanning && networks.length === 0 && (
        <div className="flex flex-col items-center justify-center p-12 text-slate-400 gap-3 rounded-2xl border border-slate-800/80 bg-slate-900/30">
          <Loader2 className="h-8 w-8 animate-spin text-cyan-400" />
          <span className="text-xs">{t('wifi_scanning_airwaves')}...</span>
        </div>
      )}

      {!scanning && networks.length === 0 && (
        <div className="flex flex-col items-center justify-center p-8 text-slate-400 gap-2 rounded-2xl border border-slate-800/80 bg-slate-900/30 text-center">
          <Radio className="h-8 w-8 text-slate-600 mb-1" />
          <strong className="text-sm text-slate-300">{t('wifi_no_networks_found')}</strong>
          <p className="text-xs max-w-sm">{t('wifi_no_networks_hint')}</p>
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-2">
        {networks.map((net: WifiNetwork) => {
          const isConnected = net.is_connected || net.ssid === currentSsid;
          const isSecured = net.security && !net.security.toLowerCase().includes('open');

          return (
            <div
              key={`${net.ssid}_${net.bssid}`}
              className={`rounded-2xl border p-4 transition flex flex-col justify-between gap-3 ${
                isConnected
                  ? 'border-emerald-400/50 bg-gradient-to-br from-emerald-950/30 via-slate-900/80 to-slate-950/90 ring-1 ring-emerald-400/40'
                  : 'border-slate-800/90 bg-slate-900/60 hover:border-slate-700 hover:bg-slate-900/80'
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3 min-w-0">
                  <div className="mt-0.5">{renderSignalBars(net.signal)}</div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <strong className="truncate font-mono text-sm font-bold text-white">{net.ssid}</strong>
                      {isConnected && (
                        <span className="rounded-full border border-emerald-400/50 bg-emerald-400/20 px-2 py-0.5 font-mono text-[9px] uppercase font-bold text-emerald-200">
                          {t('wifi_connected')}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 mt-1 text-[11px] text-slate-400 font-mono">
                      <span>{net.signal}%</span>
                      <span>•</span>
                      <span>{net.frequency}</span>
                      {net.bssid && (
                        <>
                          <span>•</span>
                          <span className="truncate max-w-[6rem]">{net.bssid}</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                <div className="shrink-0 flex items-center gap-1.5 text-slate-400">
                  {isSecured ? (
                    <span title={net.security} className="flex items-center gap-1 text-[10px] text-slate-400">
                      <Lock className="h-3.5 w-3.5 text-amber-400/80" />
                    </span>
                  ) : (
                    <span title={t('wifi_open')} className="flex items-center gap-1 text-[10px] text-emerald-400">
                      <Unlock className="h-3.5 w-3.5" />
                    </span>
                  )}
                </div>
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-slate-800/60">
                <span className="font-mono text-[10px] uppercase text-slate-500 truncate max-w-[12rem]">
                  {net.security || t('wifi_open')}
                </span>
                {isConnected ? (
                  <button
                    type="button"
                    onClick={() => void onDisconnect()}
                    disabled={connecting}
                    className="rounded-lg border border-rose-500/40 bg-rose-500/10 px-2.5 py-1 text-xs font-semibold text-rose-300 hover:bg-rose-500/20 transition disabled:opacity-50"
                  >
                    {t('wifi_disconnect')}
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => handleStartConnect(net.ssid)}
                    disabled={connecting}
                    className="rounded-lg border border-cyan-400/40 bg-cyan-400/10 px-3 py-1 text-xs font-semibold text-cyan-300 hover:bg-cyan-400/20 transition disabled:opacity-50"
                  >
                    {t('wifi_connect_btn')}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};