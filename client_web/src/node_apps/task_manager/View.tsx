import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Activity,
  AlertCircle,
  Brain,
  Camera,
  CheckCircle2,
  Cpu,
  Flame,
  HardDrive,
  Layers,
  Loader2,
  Mic,
  Network,
  RefreshCw,
  Search,
  Sparkles,
  StopCircle,
  Thermometer,
  Zap,
} from 'lucide-react';
import { ControlScope } from '../console/data/nodeConsoleApi';
import { ModuleFrame } from '../shared/components/ModuleFrame';
import { fetchNodeTasks, terminateTask, toggleNodeCapability } from './api';
import { useTaskManagerI18n } from './scope';
import { NodeCapabilities, NodeTasksSummary, ProcessCategory, SystemProcess } from './types';

interface TaskManagerViewProps {
  readonly nodeId?: string;
  readonly scope?: ControlScope;
  readonly initialPayload?: Record<string, unknown>;
}

export const View: React.FC<TaskManagerViewProps> = ({ nodeId = '', scope = 'mesh', initialPayload }) => {
  const { t } = useTaskManagerI18n();
  const targetId = nodeId || (typeof initialPayload?.nodeId === 'string' ? initialPayload.nodeId : 'virtual_core');

  const [summary, setSummary] = useState<NodeTasksSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<'all' | ProcessCategory>('all');
  const [refreshInterval, setRefreshInterval] = useState<number>(2000);
  const [terminatingPid, setTerminatingPid] = useState<number | null>(null);
  const [togglingCap, setTogglingCap] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      const data = await fetchNodeTasks(targetId);
      setSummary(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'error_loading_tasks');
    } finally {
      setLoading(false);
    }
  }, [targetId]);

  useEffect(() => {
    void loadData();
    if (refreshInterval <= 0) return;
    const timer = setInterval(() => {
      void loadData();
    }, refreshInterval);
    return () => clearInterval(timer);
  }, [loadData, refreshInterval]);

  const handleTerminate = async (pid: number, name: string) => {
    if (terminatingPid) return;
    try {
      setTerminatingPid(pid);
      await terminateTask(targetId, pid);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : `error_terminating_process ${name}`);
    } finally {
      setTerminatingPid(null);
    }
  };

  const handleToggleCapability = async (capability: keyof NodeCapabilities) => {
    if (!summary || togglingCap) return;
    const currentVal = summary.capabilities[capability];
    try {
      setTogglingCap(capability);
      const res = await toggleNodeCapability(targetId, capability, !currentVal);
      setSummary((prev) => (prev ? { ...prev, capabilities: res.capabilities } : null));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'error_toggling_capability');
    } finally {
      setTogglingCap(null);
    }
  };

  const filteredProcesses = useMemo(() => {
    if (!summary) return [];
    return summary.processes.filter((p) => {
      const matchesCategory = categoryFilter === 'all' || p.category === categoryFilter;
      const matchesSearch =
        search.trim() === '' ||
        p.name.toLowerCase().includes(search.toLowerCase()) ||
        String(p.pid).includes(search) ||
        p.user.toLowerCase().includes(search.toLowerCase());
      return matchesCategory && matchesSearch;
    });
  }, [summary, categoryFilter, search]);

  const getMetricColor = (pct: number) => {
    if (pct >= 85) return 'from-rose-500 to-amber-500 text-rose-300';
    if (pct >= 65) return 'from-amber-500 to-yellow-500 text-amber-300';
    return 'from-emerald-400 to-cyan-400 text-emerald-300';
  };

  return (
    <ModuleFrame
      icon={Activity}
      title={t('title')}
      subtitle={t('description')}
      badge={targetId ? `${targetId} (${t(`scope_${scope}`)})` : t(`scope_${scope}`)}
    >
      <div className="flex flex-col gap-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs text-slate-400">
              {t('target_node')}: <strong className="text-cyan-300">{targetId}</strong>
            </span>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <div className="flex items-center gap-1 rounded-xl border border-slate-800 bg-slate-900/80 px-2 py-1 text-xs">
              <span className="text-[11px] text-slate-400 font-mono">{t('refresh_rate')}:</span>
              {[
                { label: '1s', val: 1000 },
                { label: '2s', val: 2000 },
                { label: '5s', val: 5000 },
                { label: t('rate_pause'), val: 0 },
              ].map((opt) => (
                <button
                  key={opt.val}
                  type="button"
                  onClick={() => setRefreshInterval(opt.val)}
                  className={`rounded-lg px-2 py-0.5 text-[11px] font-semibold transition ${
                    refreshInterval === opt.val
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/40'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>

            <button
              type="button"
              onClick={() => void loadData()}
              disabled={loading}
              className="flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900/80 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:border-slate-700 hover:text-white transition disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin text-cyan-300' : ''}`} />
              {t('refresh')}
            </button>
          </div>
        </div>

        {error && (
          <div className="flex items-center gap-2 rounded-xl border border-rose-500/40 bg-rose-500/10 p-3 text-xs text-rose-300">
            <AlertCircle className="h-4 w-4 shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
        )}

        {loading && !summary && (
          <div className="flex flex-col items-center justify-center p-14 text-slate-400 gap-3">
            <Loader2 className="h-8 w-8 animate-spin text-cyan-400" />
            <span className="text-xs">{t('loading_tasks')}...</span>
          </div>
        )}

        {summary && (
          <>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <div className="rounded-2xl border border-slate-800 bg-slate-900/70 backdrop-blur-md p-4 sm:p-5 flex flex-col justify-between gap-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <span className="flex h-9 w-9 items-center justify-center rounded-xl border border-cyan-400/30 bg-cyan-400/10 text-cyan-300">
                      <Cpu className="h-5 w-5" />
                    </span>
                    <div>
                      <strong className="text-xs font-bold uppercase tracking-wider text-slate-300">CPU</strong>
                      <span className="block text-[11px] font-mono text-slate-400">
                        {summary.cpu.cores} {t('cores_logical')} • {summary.cpu.freq_mhz} MHz
                      </span>
                    </div>
                  </div>
                  <strong className={`font-mono text-2xl font-black ${getMetricColor(summary.cpu.percent)}`}>
                    {summary.cpu.percent}%
                  </strong>
                </div>

                <div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
                    <div
                      style={{ width: `${Math.min(100, summary.cpu.percent)}%` }}
                      className={`h-full rounded-full bg-gradient-to-r transition-all duration-300 ${getMetricColor(
                        summary.cpu.percent,
                      )}`}
                    />
                  </div>
                </div>
              </div>

              <div className="rounded-2xl border border-slate-800 bg-slate-900/70 backdrop-blur-md p-4 sm:p-5 flex flex-col justify-between gap-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <span className="flex h-9 w-9 items-center justify-center rounded-xl border border-purple-400/30 bg-purple-400/10 text-purple-300">
                      <HardDrive className="h-5 w-5" />
                    </span>
                    <div>
                      <strong className="text-xs font-bold uppercase tracking-wider text-slate-300">RAM</strong>
                      <span className="block text-[11px] font-mono text-slate-400">
                        {summary.ram.used_gb} GB / {summary.ram.total_gb} GB
                      </span>
                    </div>
                  </div>
                  <strong className={`font-mono text-2xl font-black ${getMetricColor(summary.ram.percent)}`}>
                    {summary.ram.percent}%
                  </strong>
                </div>

                <div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
                    <div
                      style={{ width: `${Math.min(100, summary.ram.percent)}%` }}
                      className={`h-full rounded-full bg-gradient-to-r transition-all duration-300 ${getMetricColor(
                        summary.ram.percent,
                      )}`}
                    />
                  </div>
                </div>
              </div>

              <div className="rounded-2xl border border-slate-800 bg-slate-900/70 backdrop-blur-md p-4 sm:p-5 flex flex-col justify-between gap-3 sm:col-span-2 lg:col-span-1">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-emerald-400/30 bg-emerald-400/10 text-emerald-300">
                      <Zap className="h-5 w-5" />
                    </span>
                    <div className="min-w-0">
                      <strong className="text-xs font-bold uppercase tracking-wider text-slate-300 truncate block">
                        {summary.gpu ? summary.gpu.name : t('gpu_not_detected')}
                      </strong>
                      <span className="block text-[11px] font-mono text-slate-400">
                        {summary.gpu
                          ? `${Math.round(summary.gpu.memory_used_mb)} MB / ${Math.round(summary.gpu.memory_total_mb)} MB`
                          : t('gpu_integrated_cpu')}
                      </span>
                    </div>
                  </div>
                  {summary.gpu ? (
                    <div className="text-right">
                      <strong className={`font-mono text-2xl font-black ${getMetricColor(summary.gpu.utilization_percent)}`}>
                        {summary.gpu.utilization_percent}%
                      </strong>
                      <span className="flex items-center justify-end gap-1 text-[10px] font-mono text-amber-300">
                        <Thermometer className="h-3 w-3" />
                        {summary.gpu.temperature_c}°C
                      </span>
                    </div>
                  ) : (
                    <span className="rounded-full border border-slate-700 bg-slate-800 px-2 py-0.5 text-[10px] font-mono text-slate-400">
                      CPU Render
                    </span>
                  )}
                </div>

                <div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
                    <div
                      style={{
                        width: `${
                          summary.gpu
                            ? Math.min(100, Math.round((summary.gpu.memory_used_mb / summary.gpu.memory_total_mb) * 100))
                            : 0
                        }%`,
                      }}
                      className="h-full rounded-full bg-gradient-to-r from-emerald-400 to-teal-400 transition-all duration-300"
                    />
                  </div>
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 sm:p-5">
              <div className="mb-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                    {t('mesh_workload_capabilities_title')}
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">{t('mesh_workload_capabilities_desc')}</p>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                {[
                  {
                    key: 'voice_studio' as const,
                    titleKey: 'cap_voice_studio',
                    descKey: 'cap_voice_studio_desc',
                    icon: Mic,
                    accent: 'from-amber-500/20 to-orange-500/20 text-amber-300 border-amber-500/30',
                  },
                  {
                    key: 'brain_llm' as const,
                    titleKey: 'cap_brain_llm',
                    descKey: 'cap_brain_llm_desc',
                    icon: Brain,
                    accent: 'from-cyan-500/20 to-blue-500/20 text-cyan-300 border-cyan-500/30',
                  },
                  {
                    key: 'vision_camera' as const,
                    titleKey: 'cap_vision_camera',
                    descKey: 'cap_vision_camera_desc',
                    icon: Camera,
                    accent: 'from-purple-500/20 to-pink-500/20 text-purple-300 border-purple-500/30',
                  },
                  {
                    key: 'mesh_hub' as const,
                    titleKey: 'cap_mesh_hub',
                    descKey: 'cap_mesh_hub_desc',
                    icon: Network,
                    accent: 'from-emerald-500/20 to-teal-500/20 text-emerald-300 border-emerald-500/30',
                  },
                ].map((cap) => {
                  const Icon = cap.icon;
                  const isEnabled = summary.capabilities[cap.key];
                  const isPending = togglingCap === cap.key;

                  return (
                    <div
                      key={cap.key}
                      className={`rounded-xl border p-3.5 flex flex-col justify-between gap-3 transition ${
                        isEnabled
                          ? 'border-slate-700 bg-slate-900/90'
                          : 'border-slate-800/60 bg-slate-950/40 opacity-60'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className={`flex h-8 w-8 items-center justify-center rounded-lg border ${cap.accent}`}>
                            <Icon className="h-4 w-4" />
                          </span>
                          <div>
                            <strong className="text-xs font-semibold text-white block">{t(cap.titleKey)}</strong>
                            <span className="text-[10px] text-slate-400 block line-clamp-1">{t(cap.descKey)}</span>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center justify-between pt-2 border-t border-slate-800/80">
                        <span
                          className={`text-[10px] font-mono font-bold uppercase ${
                            isEnabled ? 'text-emerald-400' : 'text-slate-500'
                          }`}
                        >
                          {isEnabled ? t('cap_enabled') : t('cap_disabled')}
                        </span>
                        <button
                          type="button"
                          onClick={() => void handleToggleCapability(cap.key)}
                          disabled={isPending}
                          className={`rounded-lg px-2.5 py-1 text-xs font-semibold transition ${
                            isEnabled
                              ? 'border border-rose-500/40 bg-rose-500/10 text-rose-300 hover:bg-rose-500/20'
                              : 'border border-emerald-500/40 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20'
                          } disabled:opacity-50`}
                        >
                          {isPending ? '...' : isEnabled ? t('disable_action') : t('enable_action')}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="flex flex-col gap-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                    {t('live_processes_title')} ({filteredProcesses.length})
                  </h3>
                </div>

                <div className="flex items-center gap-2 flex-wrap">
                  <div className="relative">
                    <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-500" />
                    <input
                      type="text"
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                      placeholder={t('search_process_placeholder')}
                      className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-1.5 pl-8 text-xs text-white placeholder-slate-500 focus:border-cyan-400 focus:outline-hidden"
                    />
                  </div>

                  <div className="flex items-center gap-1 rounded-xl border border-slate-800 bg-slate-900/80 p-0.5 text-xs">
                    {[
                      { id: 'all' as const, labelKey: 'cat_all' },
                      { id: 'ai_engine' as const, labelKey: 'cat_ai_engine' },
                      { id: 'nuxiva' as const, labelKey: 'cat_nuxiva' },
                      { id: 'system' as const, labelKey: 'cat_system' },
                    ].map((cat) => (
                      <button
                        key={cat.id}
                        type="button"
                        onClick={() => setCategoryFilter(cat.id)}
                        className={`rounded-lg px-2.5 py-1 text-xs font-semibold transition ${
                          categoryFilter === cat.id
                            ? 'bg-cyan-500/20 text-cyan-200 border border-cyan-400/40'
                            : 'text-slate-400 hover:text-white'
                        }`}
                      >
                        {t(cat.labelKey)}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900/50">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-slate-800 bg-slate-900/90 font-mono text-[11px] uppercase tracking-wider text-slate-400">
                      <th className="py-2.5 px-4 font-semibold">{t('col_process')}</th>
                      <th className="py-2.5 px-3 font-semibold">PID</th>
                      <th className="py-2.5 px-3 font-semibold">{t('col_category')}</th>
                      <th className="py-2.5 px-3 font-semibold text-right">CPU %</th>
                      <th className="py-2.5 px-3 font-semibold text-right">RAM (MB)</th>
                      <th className="py-2.5 px-3 font-semibold text-right">GPU VRAM</th>
                      <th className="py-2.5 px-3 font-semibold">{t('col_user')}</th>
                      <th className="py-2.5 px-4 font-semibold text-right">{t('col_actions')}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono">
                    {filteredProcesses.map((proc: SystemProcess) => {
                      const isTerminating = terminatingPid === proc.pid;
                      return (
                        <tr key={proc.pid} className="hover:bg-slate-800/40 transition">
                          <td className="py-2 px-4 font-sans font-semibold text-white">
                            <div className="flex items-center gap-2">
                              {proc.category === 'ai_engine' && (
                                <Sparkles className="h-3.5 w-3.5 text-cyan-400 shrink-0" />
                              )}
                              {proc.category === 'nuxiva' && <Layers className="h-3.5 w-3.5 text-purple-400 shrink-0" />}
                              <span className="truncate max-w-[14rem]">{proc.name}</span>
                            </div>
                          </td>
                          <td className="py-2 px-3 text-slate-400">{proc.pid}</td>
                          <td className="py-2 px-3">
                            <span
                              className={`rounded-md px-2 py-0.5 text-[10px] font-bold uppercase ${
                                proc.category === 'ai_engine'
                                  ? 'border border-cyan-400/40 bg-cyan-400/10 text-cyan-300'
                                  : proc.category === 'nuxiva'
                                  ? 'border border-purple-400/40 bg-purple-400/10 text-purple-300'
                                  : 'border border-slate-700 bg-slate-800 text-slate-400'
                              }`}
                            >
                              {t(`cat_${proc.category}`)}
                            </span>
                          </td>
                          <td className="py-2 px-3 text-right">
                            <span
                              className={`font-bold ${
                                proc.cpu_percent >= 50
                                  ? 'text-rose-400'
                                  : proc.cpu_percent >= 10
                                  ? 'text-amber-300'
                                  : 'text-slate-300'
                              }`}
                            >
                              {proc.cpu_percent}%
                            </span>
                          </td>
                          <td className="py-2 px-3 text-right text-slate-300">{proc.ram_mb.toLocaleString()} MB</td>
                          <td className="py-2 px-3 text-right text-slate-400">
                            {proc.gpu_memory_mb > 0 ? (
                              <span className="text-emerald-300 font-bold">{proc.gpu_memory_mb} MB</span>
                            ) : (
                              '—'
                            )}
                          </td>
                          <td className="py-2 px-3 text-slate-400 truncate max-w-[8rem]">{proc.user || '—'}</td>
                          <td className="py-2 px-4 text-right">
                            <button
                              type="button"
                              onClick={() => void handleTerminate(proc.pid, proc.name)}
                              disabled={isTerminating}
                              title={t('terminate_title')}
                              className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-2.5 py-1 text-[11px] font-sans font-semibold text-rose-300 hover:bg-rose-500/20 transition disabled:opacity-40"
                            >
                              {isTerminating ? '...' : t('terminate_action')}
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </div>
    </ModuleFrame>
  );
};

export default View;