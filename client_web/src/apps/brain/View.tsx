import React from 'react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { useBrainController } from './hooks/useBrainController';
import { MainDashboard } from './components/MainDashboard';
import { StepWizard } from './components/StepWizard';
import { SimpleOverview } from './components/SimpleOverview';
import { AutopilotWizardModal } from './components/AutopilotWizardModal';
import { Brain, CheckCircle2, Sparkles, SlidersHorizontal, Wand2 } from 'lucide-react';
import { MCP_TOOLS_CATALOG, RECOMMENDED_LOCAL_MODELS } from './defaults';

export const View: React.FC = () => {
  const { t } = useScopedI18n('apps/brain');
  const controller = useBrainController(t);

  return (
    <div className="h-full flex flex-col bg-slate-50 text-slate-900 overflow-hidden select-none font-sans">
      <header className="shrink-0 flex flex-wrap items-center justify-between border-b border-slate-200/90 bg-white/95 backdrop-blur-md px-4 sm:px-6 lg:px-8 py-3.5 shadow-xs z-20 gap-3">
        <div className="flex items-center gap-3.5">
          <div className="p-2.5 rounded-2xl bg-gradient-to-br from-indigo-600 to-fuchsia-500 text-white shadow-lg shadow-indigo-500/30 flex items-center justify-center">
            <Brain className="w-5 h-5 stroke-[2.5]" />
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-base sm:text-lg font-black tracking-tight text-slate-950">
                {t('app_name')}
              </h1>
              <span className="text-[10px] font-black uppercase tracking-widest px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-900 border border-emerald-200 shadow-2xs">
                {t('status_operational')}
              </span>
            </div>
            <p className="text-xs text-slate-600 font-medium leading-none mt-1">
              {t('app_header_desc')}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 sm:gap-3">
          <div className="flex p-1 rounded-xl bg-slate-100 border border-slate-200/80">
            <button
              type="button"
              onClick={() => controller.setViewMode('simple')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 ${
                controller.viewMode === 'simple'
                  ? 'bg-white text-indigo-900 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
              {t('mode_simple')}
            </button>
            <button
              type="button"
              onClick={() => controller.setViewMode('advanced')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 ${
                controller.viewMode === 'advanced'
                  ? 'bg-white text-indigo-900 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <SlidersHorizontal className="w-3.5 h-3.5 text-slate-500" />
              {t('mode_advanced')}
            </button>
          </div>

          <button
            type="button"
            onClick={() => controller.setWizardOpen(true)}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold shadow-xs active:scale-98 transition"
          >
            <Wand2 className="w-4 h-4" />
            <span className="hidden sm:inline">{t('wizard_header_btn')}</span>
          </button>
        </div>
      </header>

      <main className="flex-1 min-h-0 overflow-y-auto px-4 sm:px-6 lg:px-8 xl:px-10 py-5 pb-32 w-full">
        {controller.toastMessage && (
          <div className="mb-5 p-4 rounded-2xl bg-emerald-50 border border-emerald-300 text-emerald-950 text-xs sm:text-sm font-bold flex items-center gap-3 shadow-md">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
            <span className="flex-1">{controller.toastMessage}</span>
          </div>
        )}

        {controller.activeTarget ? (
          <StepWizard
            target={controller.activeTarget}
            providers={controller.providers}
            machines={controller.machines}
            modelsCatalog={controller.modelsCatalog}
            mcpCatalog={MCP_TOOLS_CATALOG}
            defaultRemoteHost={controller.remoteServers[0]?.rawInputHost || ''}
            defaultRemotePort={11434}
            onUpdateRemoteHost={() => {}}
            onUpdateRemotePort={() => {}}
            onSaveTarget={controller.handleSaveTarget}
            onUpdateApiKey={controller.handleUpdateApiKey}
            onSaveApiKey={controller.handleSaveApiKey}
            onSaveCredentials={controller.handleSaveCredentials}
            onModelInstalledOnMachine={() => {}}
            onCancel={() => controller.setActiveTarget(null)}
            t={t}
          />
        ) : controller.viewMode === 'simple' ? (
          <SimpleOverview
            globalDefault={controller.globalDefault}
            hardwareInfo={controller.hardwareInfo}
            ollamaStatus={controller.ollamaStatus}
            targets={controller.targets}
            testRunning={controller.testRunning}
            testResult={controller.testResult}
            onOpenWizard={() => controller.setWizardOpen(true)}
            onRunTest={controller.handleRunDiagnosticTest}
            onSwitchToAdvanced={() => controller.setViewMode('advanced')}
            t={t}
          />
        ) : (
          <MainDashboard
            globalDefault={controller.globalDefault}
            targets={controller.targets}
            remoteServers={controller.remoteServers}
            localModels={controller.localModels}
            recommendedModels={RECOMMENDED_LOCAL_MODELS}
            providers={controller.providers}
            mcpCatalog={MCP_TOOLS_CATALOG}
            onMakeDefaultForAll={controller.handleMakeDefaultForAll}
            onSyncAllModules={controller.handleSyncAllModules}
            onSelectTarget={(target) => controller.setActiveTarget(target)}
            onRestoreTargetDefault={controller.handleRestoreTargetDefault}
            onAddRemoteServer={controller.handleAddRemoteServer}
            onRemoveRemoteServer={controller.handleRemoveRemoteServer}
            onReloadRemoteModels={(serverId) => controller.handleReloadRemoteModels(serverId)}
            onReloadLocalModels={controller.handleReloadLocalModels}
            onUpdateApiKey={controller.handleUpdateApiKey}
            onSaveApiKey={controller.handleSaveApiKey}
            onSaveCredentials={controller.handleSaveCredentials}
            t={t}
          />
        )}
      </main>

      <AutopilotWizardModal
        isOpen={controller.wizardOpen}
        globalDefault={controller.globalDefault}
        localModels={controller.localModels}
        providers={controller.providers}
        remoteServers={controller.remoteServers}
        hardwareInfo={controller.hardwareInfo}
        onClose={() => controller.setWizardOpen(false)}
        onApply={controller.handleMakeDefaultForAll}
        onSaveApiKey={controller.handleSaveApiKey}
        t={t}
      />
    </div>
  );
};
