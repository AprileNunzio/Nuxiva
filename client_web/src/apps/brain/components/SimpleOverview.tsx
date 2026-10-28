import React from 'react';
import {
  MessageSquare,
  Sparkles,
  Mic,
  Brain,
  CheckCircle2,
  ArrowRight,
  ShieldCheck,
  Zap,
  SlidersHorizontal,
} from 'lucide-react';
import { AutonomousHeroCard } from './AutonomousHeroCard';
import { BrainGlobalDefault, HostHardwareInfo, LocalOllamaStatus, BrainTargetConfig } from '../types';

interface SimpleOverviewProps {
  readonly globalDefault: BrainGlobalDefault;
  readonly hardwareInfo: HostHardwareInfo | null;
  readonly ollamaStatus: LocalOllamaStatus | null;
  readonly targets: readonly BrainTargetConfig[];
  readonly testRunning: boolean;
  readonly testResult: { success: boolean; latencyMs: number; message: string } | null;
  readonly onOpenWizard: () => void;
  readonly onRunTest: () => void;
  readonly onSwitchToAdvanced: () => void;
  readonly t: (key: string) => string;
}

export const SimpleOverview: React.FC<SimpleOverviewProps> = ({
  globalDefault,
  hardwareInfo,
  ollamaStatus,
  targets,
  testRunning,
  testResult,
  onOpenWizard,
  onRunTest,
  onSwitchToAdvanced,
  t,
}) => {
  const getRoleIcon = (id: string) => {
    switch (id) {
      case 'fast_conversation':
        return <MessageSquare className="w-5 h-5 text-indigo-600" />;
      case 'reasoning':
        return <Sparkles className="w-5 h-5 text-purple-600" />;
      case 'live_audio':
        return <Mic className="w-5 h-5 text-teal-600" />;
      case 'cognitive_arbiter':
      default:
        return <Brain className="w-5 h-5 text-rose-600" />;
    }
  };

  return (
    <div className="space-y-6">
      <AutonomousHeroCard
        globalDefault={globalDefault}
        hardwareInfo={hardwareInfo}
        ollamaStatus={ollamaStatus}
        targets={targets}
        testRunning={testRunning}
        testResult={testResult}
        onOpenWizard={onOpenWizard}
        onRunTest={onRunTest}
        t={t}
      />

      <div>
        <div className="flex items-center justify-between mb-3.5">
          <div>
            <h3 className="text-base sm:text-lg font-black text-slate-900 tracking-tight">
              {t('roles_section_title')}
            </h3>
            <p className="text-xs text-slate-500 font-medium">
              {t('roles_section_desc')}
            </p>
          </div>
          <button
            type="button"
            onClick={onSwitchToAdvanced}
            className="inline-flex items-center gap-1.5 text-xs font-bold text-indigo-700 hover:text-indigo-900 transition"
          >
            <SlidersHorizontal className="w-3.5 h-3.5" />
            {t('switch_to_studio_btn')}
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
          {targets.map((tgt) => (
            <div
              key={tgt.id}
              className="p-4 sm:p-5 rounded-2xl border border-slate-200/90 bg-white shadow-xs hover:border-slate-300 transition flex items-start gap-4"
            >
              <div className="p-3 rounded-2xl bg-slate-50 border border-slate-100 shrink-0">
                {getRoleIcon(tgt.id)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <h4 className="text-sm font-black text-slate-900 truncate">
                    {tgt.name}
                  </h4>
                  <span className="text-[10px] font-bold text-emerald-800 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full shrink-0 flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                    {t('role_active_badge')}
                  </span>
                </div>
                <div className="text-xs text-slate-500 font-medium mt-1 line-clamp-2">
                  {t(tgt.descriptionKey) || tgt.descriptionKey}
                </div>
                <div className="mt-3 flex items-center gap-2 text-xs font-mono">
                  <span className="text-slate-400 font-sans font-bold text-[11px] uppercase tracking-wider">
                    {t('engine_label')}:
                  </span>
                  <span className="text-indigo-700 font-black truncate">
                    {tgt.assignedModel || globalDefault.modelName}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="p-5 sm:p-6 rounded-3xl bg-indigo-900 text-white relative overflow-hidden shadow-xl">
        <div className="relative z-10 flex flex-col sm:flex-row sm:items-center justify-between gap-5">
          <div className="space-y-1.5 max-w-xl">
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-indigo-300">
              <Zap className="w-4 h-4 text-amber-400" />
              {t('how_it_works_badge')}
            </div>
            <h4 className="text-base sm:text-lg font-black tracking-tight">
              {t('how_it_works_title')}
            </h4>
            <p className="text-xs sm:text-sm text-indigo-200 font-medium leading-relaxed">
              {t('how_it_works_desc')}
            </p>
          </div>
          <button
            type="button"
            onClick={onOpenWizard}
            className="shrink-0 px-5 py-2.5 rounded-xl bg-white text-indigo-950 font-black text-xs sm:text-sm shadow-md hover:bg-indigo-50 active:scale-98 transition self-start sm:self-center"
          >
            {t('reconfigure_step_btn')}
          </button>
        </div>
      </div>
    </div>
  );
};
