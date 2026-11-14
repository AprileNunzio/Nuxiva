import React from 'react';
import {
  Sparkles,
  FolderTree,
  ShieldCheck,
  Globe2,
  Layers,
  Cpu,
  Bot,
  Wrench,
  CheckCircle2,
  XCircle,
  ArrowRight
} from 'lucide-react';
import type { DeveloperGuideProps } from './types';

export const GuideOverviewSection: React.FC<DeveloperGuideProps> = ({ t }) => {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 cq-sm:grid-cols-2 cq-lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-2xl bg-[var(--md-sys-color-surface-container)] border border-[var(--md-sys-color-outline-variant)] hover:border-blue-500/40 transition-all shadow-xs">
          <div className="flex items-center gap-2 mb-2 text-blue-400 font-bold text-xs">
            <Sparkles className="w-4 h-4 shrink-0" />
            <span>{t('dev_pillar_zero_code')}</span>
          </div>
          <p className="text-xs text-[var(--md-sys-color-on-surface-variant)] leading-relaxed">
            {t('dev_pillar_zero_code_desc')}
          </p>
        </div>

        <div className="p-4 rounded-2xl bg-[var(--md-sys-color-surface-container)] border border-[var(--md-sys-color-outline-variant)] hover:border-indigo-500/40 transition-all shadow-xs">
          <div className="flex items-center gap-2 mb-2 text-indigo-400 font-bold text-xs">
            <FolderTree className="w-4 h-4 shrink-0" />
            <span>{t('dev_pillar_manifest')}</span>
          </div>
          <p className="text-xs text-[var(--md-sys-color-on-surface-variant)] leading-relaxed">
            {t('dev_pillar_manifest_desc')}
          </p>
        </div>

        <div className="p-4 rounded-2xl bg-[var(--md-sys-color-surface-container)] border border-[var(--md-sys-color-outline-variant)] hover:border-emerald-500/40 transition-all shadow-xs">
          <div className="flex items-center gap-2 mb-2 text-emerald-400 font-bold text-xs">
            <ShieldCheck className="w-4 h-4 shrink-0" />
            <span>{t('dev_pillar_zerotrust')}</span>
          </div>
          <p className="text-xs text-[var(--md-sys-color-on-surface-variant)] leading-relaxed">
            {t('dev_pillar_zerotrust_desc')}
          </p>
        </div>

        <div className="p-4 rounded-2xl bg-[var(--md-sys-color-surface-container)] border border-[var(--md-sys-color-outline-variant)] hover:border-amber-500/40 transition-all shadow-xs">
          <div className="flex items-center gap-2 mb-2 text-amber-400 font-bold text-xs">
            <Globe2 className="w-4 h-4 shrink-0" />
            <span>{t('dev_pillar_distribution')}</span>
          </div>
          <p className="text-xs text-[var(--md-sys-color-on-surface-variant)] leading-relaxed">
            {t('dev_pillar_distribution_desc')}
          </p>
        </div>
      </div>

      <div className="rounded-3xl border border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container)] p-6 space-y-4">
        <h3 className="text-sm font-bold text-[var(--md-sys-color-on-surface)] flex items-center gap-2">
          <span>Confronto Architetturale: Monolite vs Ecosistema Nuxiva</span>
        </h3>
        <div className="grid grid-cols-1 cq-md:grid-cols-2 gap-4">
          <div className="p-4 rounded-2xl bg-red-950/20 border border-red-500/20 space-y-3">
            <div className="flex items-center gap-2 text-xs font-bold text-red-400">
              <XCircle className="w-4 h-4 shrink-0" />
              <span>Sistemi Operativi Tradizionali (Monolitici)</span>
            </div>
            <ul className="text-xs text-[var(--md-sys-color-on-surface-variant)] space-y-2 leading-relaxed">
              <li className="flex items-start gap-2">
                <span className="text-red-400 font-bold">•</span>
                <span>Modifiche dirette a desktop, taskbar e pannelli di configurazione per registrare ogni nuova app.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-red-400 font-bold">•</span>
                <span>Rischio di conflitti di merge Git tra sviluppatori diversi che toccano gli stessi file centrali.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-red-400 font-bold">•</span>
                <span>Un bug o un'eccezione non gestita in un modulo può compromettere l'intera interfaccia di sistema.</span>
              </li>
            </ul>
          </div>

          <div className="p-4 rounded-2xl bg-emerald-950/20 border border-emerald-500/20 space-y-3">
            <div className="flex items-center gap-2 text-xs font-bold text-emerald-400">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>Architettura Universale Nuxiva OS (100% Modulare)</span>
            </div>
            <ul className="text-xs text-[var(--md-sys-color-on-surface-variant)] space-y-2 leading-relaxed">
              <li className="flex items-start gap-2">
                <span className="text-emerald-400 font-bold">•</span>
                <span>Ogni modulo vive nella sua cartella indipendente: zero righe di codice toccate nel core.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-emerald-400 font-bold">•</span>
                <span>Le opzioni nel pannello impostazioni si autocreano dinamicamente leggendo il manifest.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-emerald-400 font-bold">•</span>
                <span>Crash isolation per ogni finestra: se l'app fallisce, l'OS continua a funzionare perfettamente.</span>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <div className="rounded-3xl border border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container)] p-6 space-y-4">
        <h3 className="text-sm font-bold text-[var(--md-sys-color-on-surface)]">
          Le 4 Tipologie di Moduli Estensibili
        </h3>
        <div className="grid grid-cols-1 cq-sm:grid-cols-2 cq-lg:grid-cols-4 gap-4">
          <div className="p-4 rounded-2xl bg-[var(--md-sys-color-surface)] border border-[var(--md-sys-color-outline-variant)] space-y-2">
            <div className="flex items-center gap-2 text-blue-400 font-bold text-xs">
              <Layers className="w-4 h-4" />
              <span>App & Giochi 3D</span>
            </div>
            <p className="text-[11px] text-[var(--md-sys-color-on-surface-variant)] leading-relaxed">
              Interfacce complete con finestra ridimensionabile, docking a schermo e icone 3D personalizzate.
            </p>
          </div>

          <div className="p-4 rounded-2xl bg-[var(--md-sys-color-surface)] border border-[var(--md-sys-color-outline-variant)] space-y-2">
            <div className="flex items-center gap-2 text-indigo-400 font-bold text-xs">
              <Cpu className="w-4 h-4" />
              <span>Motori Algoritmici</span>
            </div>
            <p className="text-[11px] text-[var(--md-sys-color-on-surface-variant)] leading-relaxed">
              Algoritmi di ragionamento logico, motori di riconoscimento vocale e analisi musicale intercambiabili.
            </p>
          </div>

          <div className="p-4 rounded-2xl bg-[var(--md-sys-color-surface)] border border-[var(--md-sys-color-outline-variant)] space-y-2">
            <div className="flex items-center gap-2 text-emerald-400 font-bold text-xs">
              <Bot className="w-4 h-4" />
              <span>Agenti Cognitivi</span>
            </div>
            <p className="text-[11px] text-[var(--md-sys-color-on-surface-variant)] leading-relaxed">
              Agenti autonomi con ruoli esecutivi, memoria a lungo termine e facoltà decisionali proattive.
            </p>
          </div>

          <div className="p-4 rounded-2xl bg-[var(--md-sys-color-surface)] border border-[var(--md-sys-color-outline-variant)] space-y-2">
            <div className="flex items-center gap-2 text-amber-400 font-bold text-xs">
              <Wrench className="w-4 h-4" />
              <span>Plugin & System Tray</span>
            </div>
            <p className="text-[11px] text-[var(--md-sys-color-on-surface-variant)] leading-relaxed">
              Widget leggeri accanto all'orologio di sistema, connettori hardware e skill specializzate.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
