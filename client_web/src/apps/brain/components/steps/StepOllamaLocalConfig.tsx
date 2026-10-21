import React, { useState } from 'react';
import { OllamaMachine, DownloadableModel } from '../../types';
import {
  Cpu,
  Download,
  CheckCircle2,
  AlertTriangle,
  Check,
  Loader2,
  Laptop,
  Terminal,
  Activity,
} from 'lucide-react';

interface StepOllamaLocalConfigProps {
  readonly machines: readonly OllamaMachine[];
  readonly selectedMachineId: string;
  readonly onSelectMachine: (machineId: string) => void;
  readonly catalog: readonly DownloadableModel[];
  readonly selectedModelName: string;
  readonly onSelectModel: (modelName: string) => void;
  readonly onModelInstalled: (machineId: string, modelName: string) => void;
  readonly t: (key: string) => string;
}

export const StepOllamaLocalConfig: React.FC<StepOllamaLocalConfigProps> = ({
  machines,
  selectedMachineId,
  onSelectMachine,
  catalog,
  selectedModelName,
  onSelectModel,
  onModelInstalled,
  t,
}) => {
  const currentMachine = machines.find((m) => m.id === selectedMachineId) || machines[0];
  const [downloadingModelId, setDownloadingModelId] = useState<string | null>(null);
  const [downloadProgress, setDownloadProgress] = useState<number>(0);
  const [customTagInput, setCustomTagInput] = useState('');
  const [activeMessage, setActiveMessage] = useState<string | null>(null);

  const handleStartDownload = (model: DownloadableModel) => {
    setDownloadingModelId(model.id);
    setDownloadProgress(0);
    setActiveMessage(`Download ${model.name} (${model.sizeGb} GB) in corso su ${currentMachine.name}...`);

    let prog = 0;
    const interval = setInterval(() => {
      prog += 20;
      setDownloadProgress(prog);
      if (prog >= 100) {
        clearInterval(interval);
        setDownloadingModelId(null);
        setActiveMessage(`Modello ${model.name} scaricato e verificato con successo!`);
        onModelInstalled(currentMachine.id, model.name);
        onSelectModel(model.name);
        setTimeout(() => setActiveMessage(null), 4000);
      }
    }, 350);
  };

  const handleCustomPull = () => {
    if (!customTagInput.trim()) return;
    const tag = customTagInput.trim();
    setActiveMessage(`Esecuzione 'ollama pull ${tag}' su ${currentMachine.name}...`);
    setTimeout(() => {
      onModelInstalled(currentMachine.id, tag);
      onSelectModel(tag);
      setActiveMessage(`Modello ${tag} pronto per l'inferenza!`);
      setCustomTagInput('');
      setTimeout(() => setActiveMessage(null), 4000);
    }, 1500);
  };

  const getHardwareFit = (model: DownloadableModel) => {
    if (currentMachine.vramGb >= model.vramRequiredGb) {
      return {
        label: t('fit_optimal_gpu'),
        color: 'text-emerald-950 bg-emerald-100 border border-emerald-300 font-bold shadow-2xs',
        icon: <CheckCircle2 className="w-3.5 h-3.5" />,
      };
    }
    if (currentMachine.ramGb >= model.minRamGb) {
      return {
        label: t('fit_cpu_ram'),
        color: 'text-amber-950 bg-amber-100 border border-amber-300 font-bold shadow-2xs',
        icon: <AlertTriangle className="w-3.5 h-3.5" />,
      };
    }
    return {
      label: t('fit_insufficient_ram'),
      color: 'text-rose-950 bg-rose-100 border border-rose-300 font-bold shadow-2xs',
      icon: <AlertTriangle className="w-3.5 h-3.5" />,
    };
  };

  return (
    <div className="w-full space-y-7">
      {/* 1. Selezione Macchina / Nodo Hardware (Full width grid) */}
      <div className="space-y-2.5 w-full">
        <label className="text-xs uppercase font-extrabold tracking-wider text-slate-700 block">
          1. {t('select_target_machine_label')}
        </label>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5 w-full">
          {machines.map((machine) => {
            const isSelected = machine.id === currentMachine.id;
            return (
              <button
                key={machine.id}
                type="button"
                onClick={() => onSelectMachine(machine.id)}
                className={`flex flex-col justify-between p-5 rounded-2xl border text-left transition-all ${
                  isSelected
                    ? 'bg-gradient-to-br from-emerald-50/80 via-white to-emerald-50/30 border-2 border-emerald-400 ring-2 ring-emerald-200 shadow-xs'
                    : 'bg-white border-slate-200/90 hover:border-slate-300 hover:bg-slate-50 shadow-2xs'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between">
                    <div className={`p-2 rounded-xl font-black ${isSelected ? 'bg-emerald-100 text-emerald-900 border border-emerald-200' : 'bg-slate-100 text-slate-700'}`}>
                      <Laptop className="w-5 h-5" />
                    </div>
                    <span className="text-[10px] font-black uppercase px-2.5 py-0.5 rounded-full bg-slate-100 border border-slate-200 text-slate-700">
                      {machine.isLocal ? t('local_host_badge') : 'Mesh Node'}
                    </span>
                  </div>
                  <div className="text-sm sm:text-base font-black text-slate-950 mt-2.5">{machine.name}</div>
                  <div className="text-xs text-indigo-700 mt-0.5 font-mono font-bold">{machine.ip}</div>
                </div>

                <div className="mt-3.5 pt-2.5 border-t border-slate-200/80 text-xs font-semibold text-slate-600">
                  <div className="flex justify-between">
                    <span>RAM: <strong className="text-slate-950 font-bold">{machine.ramGb} GB</strong></span>
                    <span>VRAM: <strong className="text-slate-950 font-bold">{machine.vramGb} GB</strong></span>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* 2. Scheda Hardware Rilevato & Stato Ollama (MD3 Light Container) */}
      <div className="rounded-2xl border border-emerald-200 bg-gradient-to-br from-emerald-50/70 via-white to-emerald-50/20 p-5 sm:p-6 space-y-4 shadow-xs w-full">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-emerald-200/80 pb-3">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-emerald-100 text-emerald-900 border border-emerald-200 font-black">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-black text-slate-950">
                2. {t('hardware_and_service_status')} ({currentMachine.name})
              </h3>
              <p className="text-xs text-slate-600 font-medium">Specifiche hardware fisiche e porte di rete verificate in tempo reale</p>
            </div>
          </div>
          <span className="flex items-center gap-2 text-xs text-emerald-950 font-black px-3.5 py-1 rounded-full bg-emerald-100 border border-emerald-300 shadow-2xs">
            <span className="w-2 h-2 rounded-full bg-emerald-600 animate-ping" />
            Ollama {currentMachine.ollamaVersion} attivo (porta 11434)
          </span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs w-full">
          <div className="p-3.5 rounded-xl bg-white border border-slate-200 shadow-2xs">
            <span className="block text-[10px] text-slate-500 uppercase font-black">{t('cpu_cores')}</span>
            <span className="text-base sm:text-lg font-black text-slate-950 mt-0.5 block">{currentMachine.cores} Cores</span>
          </div>
          <div className="p-3.5 rounded-xl bg-white border border-slate-200 shadow-2xs">
            <span className="block text-[10px] text-slate-500 uppercase font-black">{t('system_ram')}</span>
            <span className="text-base sm:text-lg font-black text-slate-950 mt-0.5 block">{currentMachine.ramGb} GB DDR</span>
          </div>
          <div className="p-3.5 rounded-xl bg-white border border-slate-200 shadow-2xs col-span-2 md:col-span-1">
            <span className="block text-[10px] text-slate-500 uppercase font-black">{t('gpu_acceleration')}</span>
            <span className="text-xs sm:text-sm font-black text-slate-950 mt-0.5 truncate block" title={currentMachine.gpu}>
              {currentMachine.gpu}
            </span>
          </div>
          <div className="p-3.5 rounded-xl bg-white border border-slate-200 shadow-2xs col-span-2 md:col-span-1">
            <span className="block text-[10px] text-slate-500 uppercase font-black">{t('operating_system')}</span>
            <span className="text-xs sm:text-sm font-black text-slate-950 mt-0.5 truncate block">{currentMachine.os}</span>
          </div>
        </div>

        {activeMessage && (
          <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-300 text-emerald-950 text-xs sm:text-sm font-bold flex items-center gap-2.5 shadow-2xs">
            <Activity className="w-4 h-4 animate-spin shrink-0 text-emerald-700" />
            <span>{activeMessage}</span>
          </div>
        )}
      </div>

      {/* 3. Catalogo Versioni e Download in base alla Macchina (Full-width Responsive Grid) */}
      <div className="space-y-4 w-full">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <label className="text-xs uppercase font-extrabold tracking-wider text-slate-700 block">
            3. {t('model_versions_catalog_title')} ({currentMachine.name})
          </label>
          <span className="text-xs font-bold text-slate-700 bg-white px-3 py-1 rounded-full border border-slate-200 shadow-2xs">
            {currentMachine.installedModels.length} {t('models_installed_on_node')}
          </span>
        </div>

        {/* Input personalizzabile per impostare qualsiasi modello liberamente */}
        <div className="p-4 rounded-2xl border-2 border-emerald-300/80 bg-white shadow-xs space-y-2">
          <label className="text-xs font-black text-slate-900 flex items-center justify-between">
            <span>Modello Assegnato (imposta liberamente o clicca una scheda sotto):</span>
            <span className="text-[11px] font-mono font-bold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-md border border-emerald-200">
              Attivo: {selectedModelName || 'Nessuno'}
            </span>
          </label>
          <div className="flex flex-col sm:flex-row items-center gap-2.5">
            <input
              type="text"
              value={selectedModelName}
              onChange={(e) => onSelectModel(e.target.value)}
              placeholder="Digita qualsiasi modello (es. deepseek-r1:70b, qwen2.5-coder:32b, llama3.3:70b...)"
              className="flex-1 w-full px-3.5 py-2.5 text-xs sm:text-sm font-mono font-bold rounded-xl bg-slate-50 border border-slate-300 text-slate-950 focus:outline-none focus:border-emerald-500 focus:bg-white focus:ring-2 focus:ring-emerald-100"
            />
            {selectedModelName && (
              <span className="text-xs font-black text-emerald-700 flex items-center gap-1.5 px-3 py-2 rounded-xl bg-emerald-50 border border-emerald-200">
                <Check className="w-4 h-4 stroke-[3]" />
                Assegnato
              </span>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3.5 w-full">
          {catalog.map((model) => {
            const isInstalled =
              currentMachine.installedModels.includes(model.name) ||
              currentMachine.installedModels.includes(model.tag) ||
              currentMachine.installedModels.some((m) => m.toLowerCase().includes(model.id.toLowerCase()));
            const isSelected = selectedModelName === model.name || selectedModelName === model.tag;
            const fit = getHardwareFit(model);
            const isDownloading = downloadingModelId === model.id;

            return (
              <div
                key={model.id}
                className={`p-5 rounded-2xl border transition-all flex flex-col justify-between min-h-[220px] ${
                  isSelected
                    ? 'bg-gradient-to-br from-emerald-50/80 via-white to-emerald-50/30 border-2 border-emerald-400 ring-2 ring-emerald-200 shadow-xs'
                    : 'bg-white border-slate-200/90 hover:border-slate-300 hover:bg-slate-50/80 shadow-2xs'
                }`}
              >
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h4 className="text-sm sm:text-base font-black text-slate-950">{model.name}</h4>
                      <span className="text-xs text-indigo-700 font-mono font-bold block mt-0.5">{model.tag}</span>
                    </div>

                    <span className={`text-[10px] px-2 py-0.5 rounded-full shrink-0 ${fit.color}`}>
                      {fit.label}
                    </span>
                  </div>

                  <p className="text-xs font-medium text-slate-600 mt-2 line-clamp-3 leading-relaxed">
                    {model.recommendedFor}
                  </p>

                  <div className="mt-3.5 pt-2.5 border-t border-slate-200/80 flex items-center justify-between text-xs font-bold text-slate-600">
                    <span>Dim: {model.sizeGb} GB</span>
                    <span>VRAM: {model.vramRequiredGb} GB</span>
                  </div>
                </div>

                <div className="mt-4 pt-2.5 border-t border-slate-200/80 space-y-2.5">
                  {/* Download Progress Bar */}
                  {isDownloading && (
                    <div className="space-y-1">
                      <div className="w-full h-1.5 rounded-full bg-slate-200 overflow-hidden border border-slate-300">
                        <div
                          className="h-full bg-emerald-500 transition-all duration-300"
                          style={{ width: `${downloadProgress}%` }}
                        />
                      </div>
                      <span className="text-[11px] text-emerald-800 font-mono font-bold block">
                        Download in corso: {downloadProgress}%...
                      </span>
                    </div>
                  )}

                  <div className="flex items-center justify-between gap-2">
                    {isInstalled ? (
                      <button
                        type="button"
                        onClick={() => onSelectModel(model.tag || model.name)}
                        className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all shadow-2xs ${
                          isSelected
                            ? 'bg-emerald-600 text-white'
                            : 'bg-slate-900 hover:bg-slate-800 text-white'
                        }`}
                      >
                        {isSelected ? (
                          <>
                            <Check className="w-3.5 h-3.5 stroke-[3]" />
                            <span>{t('assigned_label')}</span>
                          </>
                        ) : (
                          <span>{t('assign_this_model_btn')}</span>
                        )}
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={() => handleStartDownload(model)}
                        disabled={isDownloading}
                        className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-700 text-white disabled:opacity-50 transition shadow-2xs"
                      >
                        {isDownloading ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Download className="w-3.5 h-3.5" />
                        )}
                        <span>{t('download_version_btn')}</span>
                      </button>
                    )}

                    <span className="text-xs font-bold">
                      {isInstalled ? (
                        <span className="text-emerald-700 flex items-center gap-1 font-bold">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          Pronto
                        </span>
                      ) : (
                        <span className="text-slate-500">Non scaricato</span>
                      )}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Custom pull input */}
        <div className="p-3.5 rounded-2xl border border-slate-200/90 bg-white shadow-2xs flex flex-col sm:flex-row items-center gap-2.5">
          <Terminal className="w-5 h-5 text-emerald-600 shrink-0" />
          <input
            type="text"
            placeholder={t('custom_ollama_pull_placeholder')}
            value={customTagInput}
            onChange={(e) => setCustomTagInput(e.target.value)}
            className="flex-1 w-full px-3.5 py-2 text-xs font-mono rounded-xl bg-slate-50 border border-slate-300 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-emerald-500"
          />
          <button
            type="button"
            onClick={handleCustomPull}
            className="w-full sm:w-auto px-4 py-2 text-xs font-bold rounded-xl bg-slate-900 hover:bg-slate-800 text-white flex items-center justify-center gap-1.5 transition shrink-0 shadow-2xs"
          >
            <Download className="w-4 h-4" />
            <span>{t('pull_model_btn')}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
