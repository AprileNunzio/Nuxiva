import React, { useState } from 'react';
import { AlertTriangle, CheckCircle2, CircuitBoard, Cpu, FileSpreadsheet, Layers } from 'lucide-react';
import { SchematicCanvas } from './SchematicCanvas';
import type { BoardDossier, CircuitSpec, LocalizedMessage } from '../types';

interface BoardDossierPanelProps {
  readonly t: (key: string, params?: Record<string, string | number>) => string;
  readonly dossier: BoardDossier;
  readonly circuit: CircuitSpec;
  readonly expectedVoltages: Record<string, number>;
}

function renderLocalized(
  t: (key: string, params?: Record<string, string | number>) => string,
  msg: LocalizedMessage
): string {
  if (msg.key) {
    return t(msg.key, msg.params || {});
  }
  return msg.text || '';
}

export const BoardDossierPanel: React.FC<BoardDossierPanelProps> = ({
  t,
  dossier,
  circuit,
  expectedVoltages,
}) => {
  const [activeTab, setActiveTab] = useState<'dossier' | 'schematic'>('dossier');
  const isEmpty = !dossier.title && !dossier.summary && dossier.component_count === 0;

  return (
    <aside className="flex h-full w-full flex-col overflow-hidden rounded-2xl border border-slate-800 bg-slate-950/95">
      <header className="flex items-center justify-between border-b border-slate-800 bg-slate-900/90 px-3 py-2">
        <div className="flex items-center gap-1 rounded-xl bg-slate-950 p-1 text-xs">
          <button
            type="button"
            onClick={() => setActiveTab('dossier')}
            className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 font-medium transition-colors ${
              activeTab === 'dossier'
                ? 'bg-cyan-500/20 text-cyan-300'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileSpreadsheet className="h-3.5 w-3.5" aria-hidden="true" />
            {t('tab_dossier')}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('schematic')}
            className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 font-medium transition-colors ${
              activeTab === 'schematic'
                ? 'bg-cyan-500/20 text-cyan-300'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <CircuitBoard className="h-3.5 w-3.5" aria-hidden="true" />
            {t('tab_schematic')}
          </button>
        </div>
        <span className="inline-flex items-center gap-1 rounded-full border border-slate-700 bg-slate-800 px-2.5 py-0.5 text-[11px] font-semibold text-cyan-300">
          <Cpu className="h-3 w-3" aria-hidden="true" />
          {dossier.component_count}
        </span>
      </header>

      <div className="flex-1 overflow-y-auto p-3 text-xs text-slate-200">
        {activeTab === 'schematic' ? (
          <SchematicCanvas t={t} circuit={circuit} expectedVoltages={expectedVoltages} />
        ) : isEmpty ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-slate-800 p-6 text-center text-slate-400">
            <Layers className="h-8 w-8 text-slate-600" aria-hidden="true" />
            <p>{t('dossier_empty')}</p>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-3">
              {dossier.board_kind && (
                <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-cyan-400">
                  {t('dossier_board_kind')}: {dossier.board_kind}
                </div>
              )}
              {dossier.title && (
                <h3 className="text-sm font-bold text-white">{dossier.title}</h3>
              )}
              {dossier.summary && (
                <p className="mt-1.5 leading-relaxed text-slate-300">{dossier.summary}</p>
              )}
            </div>

            {dossier.characteristics.length > 0 && (
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
                <h4 className="mb-2 font-semibold text-slate-300">
                  {t('dossier_characteristics')}
                </h4>
                <ul className="flex flex-col gap-1.5">
                  {dossier.characteristics.map((item, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-slate-300">
                      <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-cyan-400" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
              <h4 className="mb-2 font-semibold text-slate-300">{t('dossier_anomalies')}</h4>
              {dossier.anomalies.length === 0 ? (
                <div className="flex items-center gap-1.5 text-emerald-400">
                  <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                  <span>{t('no_anomalies')}</span>
                </div>
              ) : (
                <ul className="flex flex-col gap-1.5">
                  {dossier.anomalies.map((anomaly, idx) => (
                    <li
                      key={idx}
                      className="flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-950/35 px-2.5 py-1.5 text-amber-200"
                    >
                      <AlertTriangle
                        className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-400"
                        aria-hidden="true"
                      />
                      <span>{renderLocalized(t, anomaly)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}
      </div>
    </aside>
  );
};
