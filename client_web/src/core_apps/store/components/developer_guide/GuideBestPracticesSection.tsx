import React, { useState } from 'react';
import {
  ShieldCheck,
  Zap,
  CheckSquare,
  Square,
  FileCheck2,
  AlertOctagon,
  Languages,
  Layers
} from 'lucide-react';
import type { DeveloperGuideProps } from './types';

export const GuideBestPracticesSection: React.FC<DeveloperGuideProps> = ({ t }) => {
  const [checkedItems, setCheckedItems] = useState<Record<number, boolean>>({});

  const toggleItem = (idx: number) => {
    setCheckedItems((prev) => ({
      ...prev,
      [idx]: !prev[idx]
    }));
  };

  const checklist = [
    'Nessun file o registro centrale del core di Nuxiva è stato modificato o importato in modo rigido.',
    'La cartella del modulo contiene manifest.json, View.tsx, icon.png e language/{it,en,es,fr}.json.',
    'Tutte le chiavi i18n sono perfettamente simmetriche e presenti in tutte le 4 lingue.',
    'Nessun commento di codice presente nei file di produzione.',
    'Ogni file di codice rispetta rigorosamente il limite architetturale di 500 righe massime.',
    'Le capabilities dichiarate nel manifest sono strettamente minime e giustificate per Zero-Trust.'
  ];

  const completedCount = Object.values(checkedItems).filter(Boolean).length;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 rounded-2xl bg-[var(--md-sys-color-surface-container)] border border-[var(--md-sys-color-outline-variant)] space-y-2">
          <div className="flex items-center gap-2 text-amber-400 font-bold text-xs">
            <Zap className="w-4 h-4" />
            <span>{t('dev_tip_perf_title')}</span>
          </div>
          <p className="text-[11px] text-[var(--md-sys-color-on-surface-variant)] leading-relaxed">
            {t('dev_tip_perf_desc')}
          </p>
        </div>

        <div className="p-4 rounded-2xl bg-[var(--md-sys-color-surface-container)] border border-[var(--md-sys-color-outline-variant)] space-y-2">
          <div className="flex items-center gap-2 text-indigo-400 font-bold text-xs">
            <FileCheck2 className="w-4 h-4" />
            <span>{t('dev_tip_clean_title')}</span>
          </div>
          <p className="text-[11px] text-[var(--md-sys-color-on-surface-variant)] leading-relaxed">
            {t('dev_tip_clean_desc')}
          </p>
        </div>

        <div className="p-4 rounded-2xl bg-[var(--md-sys-color-surface-container)] border border-[var(--md-sys-color-outline-variant)] space-y-2">
          <div className="flex items-center gap-2 text-emerald-400 font-bold text-xs">
            <Languages className="w-4 h-4" />
            <span>{t('dev_tip_i18n_title')}</span>
          </div>
          <p className="text-[11px] text-[var(--md-sys-color-on-surface-variant)] leading-relaxed">
            {t('dev_tip_i18n_desc')}
          </p>
        </div>
      </div>

      <div className="rounded-3xl border border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container)] p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-[var(--md-sys-color-outline-variant)] pb-3">
          <div className="flex items-center gap-2">
            <CheckSquare className="w-5 h-5 text-emerald-400" />
            <h3 className="text-sm font-bold text-[var(--md-sys-color-on-surface)]">
              Checklist Pre-Rilascio per Sviluppatori Nuxiva
            </h3>
          </div>
          <span className="text-xs font-mono font-bold px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-400/30">
            {completedCount} / {checklist.length} verificati
          </span>
        </div>

        <div className="space-y-2">
          {checklist.map((item, idx) => {
            const isChecked = !!checkedItems[idx];
            return (
              <button
                key={idx}
                type="button"
                onClick={() => toggleItem(idx)}
                className={`w-full flex items-center gap-3 p-3 rounded-xl border text-left transition-all ${
                  isChecked
                    ? 'bg-emerald-950/20 border-emerald-500/30 text-[var(--md-sys-color-on-surface)]'
                    : 'bg-[var(--md-sys-color-surface)] border-[var(--md-sys-color-outline-variant)] text-[var(--md-sys-color-on-surface-variant)] hover:border-[var(--md-sys-color-outline)]'
                }`}
              >
                {isChecked ? (
                  <CheckSquare className="w-4 h-4 text-emerald-400 shrink-0" />
                ) : (
                  <Square className="w-4 h-4 text-[var(--md-sys-color-outline)] shrink-0" />
                )}
                <span className="text-xs leading-relaxed">{item}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-start gap-3">
        <AlertOctagon className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <div className="text-xs text-[var(--md-sys-color-on-surface-variant)] leading-relaxed">
          <strong className="text-[var(--md-sys-color-on-surface)] block mb-0.5">
            Budget delle Risorse & Prevenzione OOM
          </strong>
          Se il tuo modulo include modelli neurali pesanti o dataset superiori a 1 GB, specifica sempre le dimensioni stimate nel manifest (`size_gb`). Lo Store di Nuxiva consiglia e valida le risorse host prima dell'allocazione.
        </div>
      </div>
    </div>
  );
};
