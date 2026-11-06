import React, { useState } from 'react';
import { CheckCircle2, AlertTriangle, ArrowRight, ArrowLeft, Download, ShieldCheck, Cpu, HardDrive } from 'lucide-react';
import { StorePackage, StoreResources } from '../types';

interface AddonsStepInstallerModalProps {
  selectedPackages: StorePackage[];
  resources: StoreResources | null;
  onClose: () => void;
  onExecuteInstall: (packages: StorePackage[]) => Promise<void>;
  t: (key: string, params?: Record<string, any>) => string;
}

export const AddonsStepInstallerModal: React.FC<AddonsStepInstallerModalProps> = ({
  selectedPackages,
  resources,
  onClose,
  onExecuteInstall,
  t
}) => {
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [activeList, setActiveList] = useState<StorePackage[]>(selectedPackages);
  const [isInstalling, setIsInstalling] = useState<boolean>(false);
  const [completed, setCompleted] = useState<boolean>(false);

  const togglePackage = (id: string) => {
    if (activeList.some(p => p.id === id)) {
      setActiveList(activeList.filter(p => p.id !== id));
    } else {
      const found = selectedPackages.find(p => p.id === id);
      if (found) setActiveList([...activeList, found]);
    }
  };

  const totalSizeGb = Number(activeList.reduce((acc, p) => acc + p.size_gb, 0).toFixed(1));
  const hasEnoughSpace = !resources || resources.disk_free_gb >= totalSizeGb + 2;

  const handleRun = async () => {
    setIsInstalling(true);
    await onExecuteInstall(activeList);
    setIsInstalling(false);
    setCompleted(true);
    setCurrentStep(2);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-md">
      <div className="os-dialog-container w-full max-w-2xl">
        <div className="os-dialog-hero">
          <div className="os-dialog-icon-wrapper">
            <Download className="w-8 h-8" />
          </div>
          <h2 className="os-dialog-heading">
            {currentStep === 0 && (t('step_install_title') || 'Installazione Componenti')}
            {currentStep === 1 && (t('step_verify_title') || 'Verifica Risorse e Compatibilità')}
            {currentStep === 2 && (t('step_complete_title') || 'Installazione Completata')}
          </h2>
          <div className="os-stepper">
            <div className={`os-step-dot ${currentStep === 0 ? 'is-active' : ''} ${currentStep > 0 ? 'is-completed' : ''}`} />
            <div className={`os-step-dot ${currentStep === 1 ? 'is-active' : ''} ${currentStep > 1 ? 'is-completed' : ''}`} />
            <div className={`os-step-dot ${currentStep === 2 ? 'is-active' : ''}`} />
          </div>
        </div>

        <div className="p-6">
          {currentStep === 0 && (
            <div className="flex flex-col gap-3">
              <p className="text-xs text-[var(--md-sys-color-on-surface-variant)] mb-2">
                {t('step_install_desc') || 'Verifica e seleziona i componenti opzionali da installare su questo nodo.'}
              </p>
              <div className="grid grid-cols-1 gap-2.5 max-h-[320px] overflow-hidden">
                {selectedPackages.map(pkg => {
                  const isChecked = activeList.some(p => p.id === pkg.id);
                  return (
                    <label key={pkg.id} className={`os-card-addon ${isChecked ? 'is-selected' : ''}`}>
                      <div className="os-checkbox-wrapper">
                        <input
                          type="checkbox"
                          className="os-checkbox-input"
                          checked={isChecked}
                          onChange={() => togglePackage(pkg.id)}
                        />
                        <div className="os-checkbox-box">
                          <CheckCircle2 className="os-checkbox-tick" />
                        </div>
                      </div>
                      <div className="os-card-addon-info">
                        <span className="os-card-addon-name">
                          {pkg.title}
                          <span className="os-card-addon-badge">{pkg.size_gb} GB</span>
                        </span>
                        <span className="os-card-addon-desc">{pkg.description}</span>
                      </div>
                    </label>
                  );
                })}
              </div>
            </div>
          )}

          {currentStep === 1 && (
            <div className="flex flex-col gap-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="os-card">
                  <div className="flex items-center gap-3 mb-2">
                    <HardDrive className="w-5 h-5 text-[var(--md-sys-color-primary)]" />
                    <span className="font-semibold text-sm">{t('storage_status') || 'Spazio Richiesto'}</span>
                  </div>
                  <span className="text-2xl font-bold font-mono">{totalSizeGb} GB</span>
                  <span className="text-xs text-[var(--md-sys-color-on-surface-variant)] mt-1">
                    {resources ? `Disponibili: ${resources.disk_free_gb} GB` : ''}
                  </span>
                </div>
                <div className="os-card">
                  <div className="flex items-center gap-3 mb-2">
                    <Cpu className="w-5 h-5 text-[var(--md-sys-color-secondary)]" />
                    <span className="font-semibold text-sm">Componenti</span>
                  </div>
                  <span className="text-2xl font-bold font-mono">{activeList.length}</span>
                  <span className="text-xs text-[var(--md-sys-color-on-surface-variant)] mt-1">
                    {t('ready_to_provision') || 'Pronti per il deployment'}
                  </span>
                </div>
              </div>

              {!hasEnoughSpace && (
                <div className="flex items-center gap-2 rounded-xl bg-error-container p-3 text-xs text-on-error-container">
                  <AlertTriangle className="h-4 w-4 shrink-0 text-error" />
                  <span>{t('insufficient_space') || 'Spazio su disco insufficiente per completare l\'installazione.'}</span>
                </div>
              )}
            </div>
          )}

          {currentStep === 2 && (
            <div className="flex flex-col items-center text-center py-4 gap-3">
              <ShieldCheck className="w-16 h-16 text-[var(--md-sys-color-success)]" />
              <p className="text-sm font-semibold text-[var(--md-sys-color-on-surface)]">
                {t('addons_installed_success') || 'Tutti i componenti selezionati sono stati installati con successo.'}
              </p>
              <div className="flex flex-wrap justify-center gap-2 mt-2">
                {activeList.map(p => (
                  <span key={p.id} className="os-badge os-badge-success">
                    {p.title}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="os-dialog-footer">
          {currentStep < 2 ? (
            <>
              <button
                type="button"
                className="os-btn os-btn-secondary"
                onClick={currentStep === 0 ? onClose : () => setCurrentStep(0)}
                disabled={isInstalling}
              >
                <ArrowLeft className="w-4 h-4" />
                <span>{currentStep === 0 ? (t('cancel') || 'Annulla') : (t('back') || 'Indietro')}</span>
              </button>
              {currentStep === 0 ? (
                <button
                  type="button"
                  className="os-btn os-btn-primary"
                  disabled={activeList.length === 0}
                  onClick={() => setCurrentStep(1)}
                >
                  <span>{t('continue') || 'Continua'}</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              ) : (
                <button
                  type="button"
                  className="os-btn os-btn-primary"
                  disabled={!hasEnoughSpace || isInstalling}
                  onClick={handleRun}
                >
                  <Download className={`w-4 h-4 ${isInstalling ? 'animate-bounce' : ''}`} />
                  <span>{isInstalling ? (t('installing') || 'Installazione...') : (t('install_now') || 'Installa Ora')}</span>
                </button>
              )}
            </>
          ) : (
            <button
              type="button"
              className="os-btn os-btn-primary w-full"
              onClick={onClose}
            >
              <span>{t('finish') || 'Fine'}</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
