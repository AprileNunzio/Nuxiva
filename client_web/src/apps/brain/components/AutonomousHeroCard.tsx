import React from 'react';
import {
  Brain,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Play,
  Sparkles,
  Cpu,
  HardDrive,
  Activity,
  Layers,
  Wand2,
} from 'lucide-react';
import { BrainGlobalDefault, HostHardwareInfo, LocalOllamaStatus, BrainTargetConfig } from '../types';

interface AutonomousHeroCardProps {
  readonly globalDefault: BrainGlobalDefault;
  readonly hardwareInfo: HostHardwareInfo | null;
  readonly ollamaStatus: LocalOllamaStatus | null;
  readonly targets: readonly BrainTargetConfig[];
  readonly testRunning: boolean;
  readonly testResult: { success: boolean; latencyMs: number; message: string } | null;
  readonly onOpenWizard: () => void;
  readonly onRunTest: () => void;
  readonly t: (key: string) => string;
}

export const AutonomousHeroCard: React.FC<AutonomousHeroCardProps> = ({
  globalDefault,
  hardwareInfo,
  ollamaStatus,
  targets,
  testRunning,
  testResult,
  onOpenWizard,
  onRunTest,
  t,
}) => {
  const isLocalRunning = ollamaStatus?.running === true;
  const hasLocalModel = (ollamaStatus?.model_count ?? 0) > 0;
  const isCloudConfigured = globalDefault.provider === 'api_key';
  const isReady =
    (globalDefault.provider === 'ollama_local' && isLocalRunning && hasLocalModel) ||
    (globalDefault.provider === 'ollama_remote') ||
    isCloudConfigured;

  const providerLabel =
    globalDefault.provider === 'ollama_local'
      ? t('provider_ollama_local')
      : globalDefault.provider === 'ollama_remote'
        ? t('provider_ollama_remote')
        : t('provider_cloud_api');

  return (
    <div className="relative overflow-hidden rounded-3xl border border-slate-200/90 bg-gradient-to-br from-white via-slate-50 to-indigo-50/40 p-5 sm:p-7 shadow-lg shadow-indigo-500/5">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 pb-6 border-b border-slate-200/80">
        <div className="flex items-start gap-4 sm:gap-5">
          <div
            className={`p-3.5 sm:p-4 rounded-3xl text-white shadow-xl flex items-center justify-center shrink-0 ${
              isReady
                ? 'bg-gradient-to-br from-emerald-500 to-teal-600 shadow-emerald-500/25'
                : 'bg-gradient-to-br from-amber-500 to-orange-600 shadow-amber-500/25'
            }`}
          >
            {isReady ? (
              <ShieldCheck className="w-8 h-8 stroke-[2.2]" />
            ) : (
              <AlertTriangle className="w-8 h-8 stroke-[2.2]" />
            )}
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2.5">
              <span
                className={`text-[11px] font-black uppercase tracking-wider px-3 py-1 rounded-full border shadow-2xs ${
                  isReady
                    ? 'bg-emerald-100/90 text-emerald-950 border-emerald-300'
                    : 'bg-amber-100/90 text-amber-950 border-amber-300'
                }`}
              >
                {isReady ? t('autonomous_badge_operational') : t('autonomous_badge_attention')}
              </span>
              <span className="text-[11px] font-bold text-slate-500 bg-white/80 border border-slate-200 px-2.5 py-0.5 rounded-full">
                {t('autonomous_mode_label')}
              </span>
            </div>
            <h2 className="text-xl sm:text-2xl font-black text-slate-950 tracking-tight mt-2">
              {isReady ? t('autonomous_title_ready') : t('autonomous_title_needs_config')}
            </h2>
            <p className="text-xs sm:text-sm text-slate-600 font-medium max-w-2xl mt-1 leading-relaxed">
              {isReady ? t('autonomous_desc_ready') : t('autonomous_desc_needs_config')}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap sm:flex-nowrap items-center gap-3 shrink-0">
          <button
            type="button"
            onClick={onRunTest}
            disabled={testRunning}
            className="flex-1 sm:flex-none inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-xs sm:text-sm font-bold shadow-xs active:scale-98 transition"
          >
            <Activity className={`w-4 h-4 text-indigo-600 ${testRunning ? 'animate-spin' : ''}`} />
            {testRunning ? t('testing_running') : t('test_brain_btn')}
          </button>
          <button
            type="button"
            onClick={onOpenWizard}
            className="flex-1 sm:flex-none inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs sm:text-sm font-extrabold shadow-md shadow-indigo-600/25 active:scale-98 transition"
          >
            <Wand2 className="w-4 h-4" />
            {t('open_wizard_btn')}
          </button>
        </div>
      </div>

      {testResult && (
        <div
          className={`mt-4 p-3.5 rounded-2xl border text-xs sm:text-sm font-semibold flex items-center justify-between gap-3 ${
            testResult.success
              ? 'bg-emerald-50 text-emerald-950 border-emerald-200'
              : 'bg-rose-50 text-rose-950 border-rose-200'
          }`}
        >
          <div className="flex items-center gap-2.5">
            {testResult.success ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
            )}
            <span>{testResult.message}</span>
          </div>
          <span className="text-xs font-mono px-2 py-0.5 rounded-md bg-white/70 border border-slate-200/60 text-slate-700">
            {testResult.latencyMs} ms
          </span>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5 mt-5">
        <div className="p-3.5 rounded-2xl bg-white/80 border border-slate-200/90 shadow-2xs">
          <div className="flex items-center gap-2 text-slate-500 text-xs font-bold uppercase tracking-wider mb-1">
            <Brain className="w-3.5 h-3.5 text-indigo-600" />
            {t('active_engine_label')}
          </div>
          <div className="text-sm font-black text-slate-900 truncate">
            {providerLabel}
          </div>
          <div className="text-xs text-indigo-700 font-bold truncate mt-0.5">
            {globalDefault.modelName}
          </div>
        </div>

        <div className="p-3.5 rounded-2xl bg-white/80 border border-slate-200/90 shadow-2xs">
          <div className="flex items-center gap-2 text-slate-500 text-xs font-bold uppercase tracking-wider mb-1">
            <Cpu className="w-3.5 h-3.5 text-indigo-600" />
            {t('cpu_hardware_label')}
          </div>
          <div className="text-sm font-black text-slate-900 truncate">
            {hardwareInfo?.cpu?.cores_logical ? `${hardwareInfo.cpu.cores_logical} ${t('cores_logical')}` : 'CPU Standard'}
          </div>
          <div className="text-xs text-slate-500 font-medium truncate mt-0.5">
            {hardwareInfo?.cpu?.has_avx2 ? 'SIMD AVX2 Attivo' : 'Vettorializzazione base'}
          </div>
        </div>

        <div className="p-3.5 rounded-2xl bg-white/80 border border-slate-200/90 shadow-2xs">
          <div className="flex items-center gap-2 text-slate-500 text-xs font-bold uppercase tracking-wider mb-1">
            <HardDrive className="w-3.5 h-3.5 text-indigo-600" />
            {t('ram_hardware_label')}
          </div>
          <div className="text-sm font-black text-slate-900 truncate">
            {hardwareInfo?.memory?.total_mb
              ? `${Math.round(hardwareInfo.memory.total_mb / 1024)} GB RAM`
              : 'Memoria Host'}
          </div>
          <div className="text-xs text-slate-500 font-medium truncate mt-0.5">
            {hardwareInfo?.gpu?.detected
              ? `${hardwareInfo.gpu.name || 'GPU Dedicata'}`
              : t('cpu_inference_mode')}
          </div>
        </div>

        <div className="p-3.5 rounded-2xl bg-white/80 border border-slate-200/90 shadow-2xs">
          <div className="flex items-center gap-2 text-slate-500 text-xs font-bold uppercase tracking-wider mb-1">
            <Layers className="w-3.5 h-3.5 text-indigo-600" />
            {t('coverage_label')}
          </div>
          <div className="text-sm font-black text-emerald-800 flex items-center gap-1.5 truncate">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            {targets.length} {t('roles_assigned')}
          </div>
          <div className="text-xs text-slate-500 font-medium truncate mt-0.5">
            {t('zero_touch_managed')}
          </div>
        </div>
      </div>
    </div>
  );
};
