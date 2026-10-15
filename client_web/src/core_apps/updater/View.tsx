import React, { useEffect, useState } from 'react';
import {
  RefreshCw,
  Clock,
  ShieldCheck,
  Cpu,
  Server,
  Terminal,
  CheckCircle2,
  AlertTriangle,
  Play,
  Save,
  HardDrive,
  Wifi,
} from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import {
  fetchUpdateStatus,
  checkForUpdates,
  saveSchedulePolicy,
  runCollaudoDiagnostics,
  triggerClusterUpdate,
} from './api';
import { UpdateStatus, CollaudoResult } from './types';

export const View: React.FC = () => {
  const { t } = useScopedI18n('core_apps/updater');

  const [status, setStatus] = useState<UpdateStatus | null>(null);
  const [collaudo, setCollaudo] = useState<CollaudoResult | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [checking, setChecking] = useState<boolean>(false);
  const [savingPolicy, setSavingPolicy] = useState<boolean>(false);
  const [runningCollaudo, setRunningCollaudo] = useState<boolean>(false);
  const [triggering, setTriggering] = useState<boolean>(false);
  const [policyMessage, setPolicyMessage] = useState<string | null>(null);

  // Form state
  const [scheduledTime, setScheduledTime] = useState<string>('03:00');
  const [synchronized, setSynchronized] = useState<boolean>(true);
  const [autoRollback, setAutoRollback] = useState<boolean>(true);
  const [channel, setChannel] = useState<string>('stable');

  const loadData = async () => {
    try {
      setLoading(true);
      const res = await fetchUpdateStatus();
      setStatus(res);
      setScheduledTime(res.scheduled_time || '03:00');
      setSynchronized(res.synchronized ?? true);
      setAutoRollback(res.auto_rollback ?? true);
      setChannel(res.channel || 'stable');
    } catch (err) {
      console.error('Failed to load update status:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCheckUpdates = async () => {
    try {
      setChecking(true);
      const res = await checkForUpdates();
      setStatus(res);
    } catch (err) {
      console.error('Check updates failed:', err);
    } finally {
      setChecking(false);
    }
  };

  const handleSavePolicy = async () => {
    try {
      setSavingPolicy(true);
      const res = await saveSchedulePolicy({
        scheduled_time: scheduledTime,
        synchronized,
        auto_rollback: autoRollback,
        channel,
      });
      setStatus(res);
      setPolicyMessage(t('policy_saved'));
      setTimeout(() => setPolicyMessage(null), 3000);
    } catch (err) {
      console.error('Save policy failed:', err);
    } finally {
      setSavingPolicy(false);
    }
  };

  const handleRunCollaudo = async () => {
    try {
      setRunningCollaudo(true);
      const res = await runCollaudoDiagnostics();
      setCollaudo(res);
      // Reload logs
      const updated = await fetchUpdateStatus();
      setStatus(updated);
    } catch (err) {
      console.error('Collaudo diagnostics failed:', err);
    } finally {
      setRunningCollaudo(false);
    }
  };

  const handleTriggerUpdate = async () => {
    try {
      setTriggering(true);
      const res = await triggerClusterUpdate(true);
      setStatus(res);
    } catch (err) {
      console.error('Trigger update failed:', err);
    } finally {
      setTriggering(false);
    }
  };

  if (loading && !status) {
    return (
      <div className="flex items-center justify-center min-h-[500px]">
        <div className="flex flex-col items-center gap-4">
          <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin" />
          <span className="text-sm font-mono text-cyan-300">{t('checking')}</span>
        </div>
      </div>
    );
  }

  const isUpToDate = !status?.update_available;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 font-mono text-slate-100">
      {/* Top Futuristic Header Banner */}
      <div className="relative overflow-hidden rounded-2xl border border-cyan-500/30 bg-slate-900/80 backdrop-blur-xl p-6 shadow-[0_0_35px_rgba(6,182,212,0.15)]">
        <div className="absolute -right-16 -top-16 w-64 h-64 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
          <div className="flex items-center gap-4">
            <div className="relative p-3.5 rounded-xl bg-cyan-500/10 border border-cyan-400/40 text-cyan-400 shadow-[0_0_15px_rgba(6,182,212,0.3)]">
              <RefreshCw className={`w-8 h-8 ${checking ? 'animate-spin' : ''}`} />
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold tracking-tight text-white">{t('title')}</h1>
                <span className="px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wider rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                  {status?.channel || channel}
                </span>
              </div>
              <p className="text-sm text-slate-400 mt-1">{t('description')}</p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-4 w-full lg:w-auto">
            <div className="flex items-center gap-3 px-4 py-2 rounded-xl bg-slate-800/80 border border-slate-700/80">
              <div className="text-xs">
                <span className="text-slate-400 block">{t('current_version')}:</span>
                <span className="font-bold text-cyan-300">{status?.current_version || '5.2.0'}</span>
              </div>
              <div className="h-6 w-px bg-slate-700" />
              <div className="text-xs">
                <span className="text-slate-400 block">{t('target_version')}:</span>
                <span className={`font-bold ${isUpToDate ? 'text-emerald-400' : 'text-amber-400'}`}>
                  {status?.latest_version || '5.2.0'}
                </span>
              </div>
            </div>

            <button
              onClick={handleCheckUpdates}
              disabled={checking}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-400/50 transition-all font-semibold text-sm shadow-[0_0_15px_rgba(6,182,212,0.2)] disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${checking ? 'animate-spin' : ''}`} />
              <span>{checking ? t('checking') : t('check_now')}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Main Grid: Scheduler & Collaudo Diagnostic Suite */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 03:00 Synchronized Scheduler Card */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md p-6 flex flex-col justify-between shadow-lg">
          <div>
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-400/30 text-indigo-400">
                <Clock className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-white">{t('schedule_title')}</h2>
                <p className="text-xs text-slate-400">{t('schedule_desc')}</p>
              </div>
            </div>

            <div className="space-y-4 my-6">
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                  {t('default_time_label')}
                </label>
                <div className="relative">
                  <input
                    type="time"
                    value={scheduledTime}
                    onChange={(e) => setScheduledTime(e.target.value)}
                    className="w-full bg-slate-800/90 border border-slate-700 rounded-xl px-4 py-2.5 text-white font-mono focus:outline-none focus:border-indigo-400"
                  />
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-800/40 border border-slate-700/60 flex items-center justify-between">
                <span className="text-xs text-slate-200">{t('sync_toggle_label')}</span>
                <input
                  type="checkbox"
                  checked={synchronized}
                  onChange={(e) => setSynchronized(e.target.checked)}
                  className="w-5 h-5 accent-cyan-400 rounded cursor-pointer"
                />
              </div>

              <div className="p-3.5 rounded-xl bg-slate-800/40 border border-slate-700/60 flex items-center justify-between">
                <span className="text-xs text-slate-200">{t('rollback_toggle_label')}</span>
                <input
                  type="checkbox"
                  checked={autoRollback}
                  onChange={(e) => setAutoRollback(e.target.checked)}
                  className="w-5 h-5 accent-cyan-400 rounded cursor-pointer"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                  {t('channel_label')}
                </label>
                <select
                  value={channel}
                  onChange={(e) => setChannel(e.target.value)}
                  className="w-full bg-slate-800/90 border border-slate-700 rounded-xl px-4 py-2.5 text-white font-mono focus:outline-none focus:border-indigo-400"
                >
                  <option value="stable">Stable (Consigliato per la casa)</option>
                  <option value="release-candidate">Release Candidate (RC)</option>
                  <option value="edge-dev">Edge Dev (Sperimentale)</option>
                </select>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-800 flex items-center justify-between">
            {policyMessage && (
              <span className="text-xs text-emerald-400 flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4" /> {policyMessage}
              </span>
            )}
            <button
              onClick={handleSavePolicy}
              disabled={savingPolicy}
              className="ml-auto flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-500/20 hover:bg-indigo-500/30 text-indigo-300 border border-indigo-400/40 transition-all font-semibold text-xs disabled:opacity-50"
            >
              <Save className="w-4 h-4" />
              <span>{savingPolicy ? t('saving') : t('save_policy')}</span>
            </button>
          </div>
        </div>

        {/* Integrated Collaudo / Hardware Diagnostic Suite */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md p-6 flex flex-col justify-between shadow-lg">
          <div>
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-400/30 text-emerald-400">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-white">{t('collaudo_title')}</h2>
                <p className="text-xs text-slate-400">{t('collaudo_desc')}</p>
              </div>
            </div>

            {/* Diagnostic gauges */}
            <div className="space-y-3 my-4">
              {collaudo ? (
                collaudo.tests.map((test) => (
                  <div
                    key={test.id}
                    className="p-3 rounded-xl bg-slate-800/50 border border-slate-700/60 flex items-center justify-between"
                  >
                    <div className="flex items-center gap-3">
                      {test.status === 'PASS' ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      ) : (
                        <AlertTriangle className="w-4 h-4 text-amber-400" />
                      )}
                      <div>
                        <div className="text-xs font-bold text-white">{test.name}</div>
                        <div className="text-[11px] text-slate-400">{test.detail}</div>
                      </div>
                    </div>
                    <span
                      className={`text-xs font-mono px-2 py-0.5 rounded border ${
                        test.status === 'PASS'
                          ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                          : 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                      }`}
                    >
                      {test.metric}
                    </span>
                  </div>
                ))
              ) : (
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 rounded-xl bg-slate-800/40 border border-slate-700/50">
                    <div className="flex items-center gap-2 text-cyan-400 mb-1">
                      <Cpu className="w-4 h-4" />
                      <span className="text-xs font-semibold">RAM Headroom</span>
                    </div>
                    <span className="text-sm font-bold text-slate-200">Pre-Check Ready</span>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-800/40 border border-slate-700/50">
                    <div className="flex items-center gap-2 text-indigo-400 mb-1">
                      <HardDrive className="w-4 h-4" />
                      <span className="text-xs font-semibold">Disk Space</span>
                    </div>
                    <span className="text-sm font-bold text-slate-200">Staging Ready</span>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-800/40 border border-slate-700/50">
                    <div className="flex items-center gap-2 text-emerald-400 mb-1">
                      <Wifi className="w-4 h-4" />
                      <span className="text-xs font-semibold">Interface IP</span>
                    </div>
                    <span className="text-sm font-bold text-slate-200">Active Route</span>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-800/40 border border-slate-700/50">
                    <div className="flex items-center gap-2 text-purple-400 mb-1">
                      <Server className="w-4 h-4" />
                      <span className="text-xs font-semibold">Rust CRDT Bus</span>
                    </div>
                    <span className="text-sm font-bold text-slate-200">Synchronized</span>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="pt-4 border-t border-slate-800 flex items-center justify-between">
            {collaudo && (
              <span
                className={`text-xs font-bold ${
                  collaudo.all_passed ? 'text-emerald-400' : 'text-amber-400'
                }`}
              >
                {collaudo.all_passed ? t('collaudo_all_passed') : t('collaudo_warnings')}
              </span>
            )}
            <button
              onClick={handleRunCollaudo}
              disabled={runningCollaudo}
              className="ml-auto flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-400/40 transition-all font-semibold text-xs disabled:opacity-50"
            >
              <ShieldCheck className={`w-4 h-4 ${runningCollaudo ? 'animate-spin' : ''}`} />
              <span>{runningCollaudo ? t('collaudo_running') : t('run_collaudo')}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Multi-Node Cluster Matrix */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md p-6 shadow-lg">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
          <div>
            <h2 className="text-lg font-bold text-white">{t('nodes_matrix_title')}</h2>
            <p className="text-xs text-slate-400">{t('nodes_matrix_desc')}</p>
          </div>

          <button
            onClick={handleTriggerUpdate}
            disabled={triggering}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500/30 to-indigo-500/30 hover:from-cyan-500/40 hover:to-indigo-500/40 text-cyan-200 border border-cyan-400/50 font-bold text-xs transition-all shadow-[0_0_20px_rgba(6,182,212,0.2)] disabled:opacity-50"
          >
            <Play className={`w-4 h-4 ${triggering ? 'animate-spin' : ''}`} />
            <span>{triggering ? t('triggering') : t('trigger_cluster_update')}</span>
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {status?.nodes && status.nodes.length > 0 ? (
            status.nodes.map((node) => (
              <div
                key={node.id}
                className="p-4 rounded-xl bg-slate-800/40 border border-slate-700/60 hover:border-cyan-500/40 transition-all"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Server className="w-4 h-4 text-cyan-400" />
                    <span className="font-bold text-sm text-white truncate max-w-[150px]">
                      {node.name}
                    </span>
                  </div>
                  <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                    {t('status_ready')}
                  </span>
                </div>

                <div className="text-xs text-slate-400 space-y-1 mb-3">
                  <div>
                    <span className="text-slate-500">Tier: </span>
                    <span className="text-slate-300">{node.tier}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">IP: </span>
                    <span className="text-slate-300">{node.ip}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">Versione: </span>
                    <span className="text-cyan-300">{node.current_version}</span>
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-700/60 flex items-center justify-between text-[11px]">
                  <span className="text-slate-400">Collaudo Pre-Flight:</span>
                  <span className="text-emerald-400 flex items-center gap-1 font-semibold">
                    <CheckCircle2 className="w-3.5 h-3.5" /> OK
                  </span>
                </div>
              </div>
            ))
          ) : (
            <div className="col-span-full py-8 text-center text-slate-400 text-sm">
              Nessun nodo collegato rilevato.
            </div>
          )}
        </div>
      </div>

      {/* Futuristic Rollout Terminal */}
      <div className="rounded-2xl border border-slate-800 bg-black/90 p-5 shadow-2xl font-mono">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-3">
          <div className="flex items-center gap-2 text-xs font-bold text-slate-300">
            <Terminal className="w-4 h-4 text-cyan-400" />
            <span>{t('terminal_title')}</span>
          </div>
          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800 animate-pulse">
            {t('terminal_live')}
          </span>
        </div>

        <div className="h-40 overflow-y-auto space-y-1.5 text-xs text-slate-300 pr-2">
          {status?.logs && status.logs.length > 0 ? (
            status.logs.map((log, idx) => (
              <div key={idx} className="flex items-start gap-2">
                <span className="text-slate-600">[{new Date(log.timestamp * 1000).toLocaleTimeString()}]</span>
                <span
                  className={`font-semibold ${
                    log.level === 'WARNING'
                      ? 'text-amber-400'
                      : log.level === 'ERROR'
                      ? 'text-red-400'
                      : 'text-cyan-400'
                  }`}
                >
                  [{log.level}]
                </span>
                <span className="text-slate-300">{log.message}</span>
              </div>
            ))
          ) : (
            <div className="text-slate-600 italic">In attesa di eventi di telemetria...</div>
          )}
        </div>
      </div>
    </div>
  );
};
