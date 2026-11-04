import React from 'react';
import { ShieldAlert, X } from 'lucide-react';
import { StorePackage, StoreInstallResponse, StoreResources } from '../types';

interface MemoryAdvisoryModalProps {
  advisoryData: {
    pkg: StorePackage;
    response: StoreInstallResponse;
  };
  resources: StoreResources | null;
  onClose: () => void;
  onConfirmForce: (pkg: StorePackage) => void;
  t: (key: string, params?: Record<string, any>) => string;
}

export const MemoryAdvisoryModal: React.FC<MemoryAdvisoryModalProps> = ({
  advisoryData,
  resources,
  onClose,
  onConfirmForce,
  t
}) => {
  return (
    <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs z-50 flex items-center justify-center p-4">
      <div className="bg-white border border-amber-300 rounded-2xl shadow-2xl max-w-lg w-full p-6 text-slate-800 flex flex-col gap-4">
        <div className="flex items-start gap-3.5">
          <div className="p-2.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-600 shrink-0">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div className="flex-1">
            <h3 className="text-base font-bold text-slate-900">
              {t('modal_advisory_title')}
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              {t('modal_advisory_subtitle')}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1 rounded-lg transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-3.5 bg-amber-50/70 border border-amber-200/80 rounded-xl text-xs text-slate-700 leading-relaxed font-medium">
          {advisoryData.response.message}
        </div>

        <div className="grid grid-cols-2 gap-3 p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs font-mono">
          <div>
            <span className="text-[10px] text-slate-400 block font-sans uppercase tracking-wider font-bold">
              {t('modal_detected_ram')}
            </span>
            <span className="text-amber-600 font-bold text-sm">
              {advisoryData.response.ram_total_gb ?? resources?.ram_total_gb ?? 0} GB
            </span>
          </div>
          <div>
            <span className="text-[10px] text-slate-400 block font-sans uppercase tracking-wider font-bold">
              {t('modal_recommended_ram')}
            </span>
            <span className="text-emerald-600 font-bold text-sm">
              {advisoryData.response.recommended_ram_gb ?? 8.0} GB
            </span>
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition"
          >
            {t('modal_cancel')}
          </button>
          <button
            onClick={() => {
              const pkg = advisoryData.pkg;
              onClose();
              onConfirmForce(pkg);
            }}
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-amber-600 hover:bg-amber-500 active:scale-95 text-white transition shadow-xs"
          >
            {t('modal_confirm_force')}
          </button>
        </div>
      </div>
    </div>
  );
};
