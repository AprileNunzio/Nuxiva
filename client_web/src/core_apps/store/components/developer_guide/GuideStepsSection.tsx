import React, { useState } from 'react';
import {
  FolderTree,
  FileCode2,
  Sliders,
  AppWindow,
  ShieldCheck,
  Rocket,
  CheckCircle2,
  ChevronRight,
  Info
} from 'lucide-react';
import type { DeveloperGuideProps } from './types';

export const GuideStepsSection: React.FC<DeveloperGuideProps> = ({ t }) => {
  const [expandedStep, setExpandedStep] = useState<number>(1);

  const steps = [
    {
      num: 1,
      icon: FolderTree,
      color: 'text-blue-400',
      bgColor: 'bg-blue-500/15',
      borderColor: 'border-blue-500/30',
      title: t('dev_step_1_title'),
      summary: t('dev_step_1_desc'),
      details: [
        'Crea la cartella dedicata in client_web/src/apps/[tua_app]/ (oppure src/engines/, src/agents/, src/plugins/).',
        'La cartella deve essere completamente autonoma: contiene manifest.json, View.tsx, icon.png e la cartella language/.',
        'Nessuna dipendenza hardcoded: non importare file interni del core né registrare manualmente percorsi in file centrali.'
      ],
      codeSnippet: `client_web/src/apps/il_mio_modulo/
├── manifest.json
├── View.tsx
├── icon.png
└── language/
    ├── it.json
    ├── en.json
    ├── es.json
    └── fr.json`
    },
    {
      num: 2,
      icon: FileCode2,
      color: 'text-indigo-400',
      bgColor: 'bg-indigo-500/15',
      borderColor: 'border-indigo-500/30',
      title: t('dev_step_2_title'),
      summary: t('dev_step_2_desc'),
      details: [
        'Dichiara nel manifest le proprietà fondamentali: id, name, version, kind, category e author.',
        'Imposta placement: { desktop: true } per aggiungere automaticamente la scorciatoia sul desktop di Nuxiva.',
        'Configura taskbar: { pinned: true } per la barra applicazioni, oppure taskbar: { tray: true } per posizionarla nell\'area di stato accanto all\'orologio.',
        'Definisci le dimensioni predefinite della finestra, minWidth, minHeight e le facoltà di ridimensionamento.'
      ],
      codeSnippet: `"placement": {
  "desktop": true,
  "taskbar": {
    "pinned": true,
    "tray": false
  },
  "control_panel": {
    "show": true,
    "category": "productivity"
  }
}`
    },
    {
      num: 3,
      icon: Sliders,
      color: 'text-amber-400',
      bgColor: 'bg-amber-500/15',
      borderColor: 'border-amber-500/30',
      title: t('dev_step_3_title'),
      summary: t('dev_step_3_desc'),
      details: [
        'La logica universale di Nuxiva: il pannello Impostazioni NON deve contenere codice cablato per le opzioni delle singole app.',
        'Inserisci semplicemente l\'array "options" nel tuo manifest.json specificando id, type, default, label_key e desc_key.',
        'Tipi supportati: "boolean" (crea uno switch on/off), "range" (crea uno slider numerico graduato), "select" (menu a tendina).',
        'Il sistema operativo genera automaticamente i controlli e li salva nello stato di runtime isolato dell\'applicazione.'
      ],
      codeSnippet: `"options": [
  {
    "id": "high_contrast_mode",
    "type": "boolean",
    "default": false,
    "label_key": "opt_contrast_label",
    "desc_key": "opt_contrast_desc"
  },
  {
    "id": "refresh_rate",
    "type": "range",
    "default": 30,
    "min": 10,
    "max": 60,
    "step": 5,
    "label_key": "opt_refresh_label",
    "desc_key": "opt_refresh_desc"
  }
]`
    },
    {
      num: 4,
      icon: AppWindow,
      color: 'text-emerald-400',
      bgColor: 'bg-emerald-500/15',
      borderColor: 'border-emerald-500/30',
      title: t('dev_step_4_title'),
      summary: t('dev_step_4_desc'),
      details: [
        'Esporta sempre un componente nominato "View" in View.tsx: export function View() { ... }.',
        'Usa l\'hook useScopedI18n("nome_modulo") per accedere alle traduzioni localizzate del tuo modulo.',
        'Usa useOSApp() per interagire con l\'ambiente della finestra: titolo dinamico, breadcrumb di navigazione e ricerca.',
        'Evita librerie esterne pesanti che possano appesantire il bundle: usa Tailwind e Lucide Icons già inclusi.'
      ],
      codeSnippet: `import React from 'react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { useOSApp } from '../../app_shell/window_manager/WindowContext';

export function View() {
  const { t } = useScopedI18n('il_mio_modulo');
  const os = useOSApp();
  return (
    <div className="p-4 space-y-4">
      <h2 className="text-base font-bold">{t('greeting')}</h2>
    </div>
  );
}`
    },
    {
      num: 5,
      icon: ShieldCheck,
      color: 'text-purple-400',
      bgColor: 'bg-purple-500/15',
      borderColor: 'border-purple-500/30',
      title: t('dev_step_5_title'),
      summary: t('dev_step_5_desc'),
      details: [
        'Architettura Zero-Trust: dichiara nel manifest solo le "capabilities" strettamente necessarie al funzionamento.',
        'Se un\'app richiede "network_fetch" o "audio_output", il kernel verifica che l\'utente o il ruolo di sicurezza lo consenta.',
        'Crash Isolation: ogni applicazione viene racchiusa in un WindowErrorBoundary dedicato. Un eventuale crash del tuo codice non comprometterà mai il sistema operativo.',
        'Gli errori vengono intercettati e inviati in sicurezza a reportError() sull\'errorBus di Nuxiva.'
      ],
      codeSnippet: `"capabilities": [
  "local_storage",
  "webgl2",
  "audio_output"
]`
    },
    {
      num: 6,
      icon: Rocket,
      color: 'text-rose-400',
      bgColor: 'bg-rose-500/15',
      borderColor: 'border-rose-500/30',
      title: t('dev_step_6_title'),
      summary: t('dev_step_6_desc'),
      details: [
        'Scansione all\'avvio: il motore di discovery rileva istantaneamente la cartella tramite import.meta.glob senza ricompilare nulla.',
        'Distribuzione Indipendente: carica la tua cartella su qualsiasi repository Git pubblico o privato.',
        'Aggiunta allo Store: gli utenti possono aggiungere il tuo repository nella scheda "Sorgenti & Repository" dello Store con 1 clic.',
        'Verifica delle Risorse: Nuxiva Store convalida automaticamente spazio disco e RAM prima di consentire l\'installazione.'
      ],
      codeSnippet: `git init
git add .
git commit -m "feat: release mio_modulo v1.0.0"
git remote add origin https://github.com/tuo-utente/mio-modulo.git
git push -u origin main`
    }
  ];

  return (
    <div className="space-y-4">
      <div className="p-4 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-start gap-3">
        <Info className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />
        <div className="text-xs text-[var(--md-sys-color-on-surface-variant)] leading-relaxed">
          <strong className="text-[var(--md-sys-color-on-surface)] block mb-0.5">
            Il Workflow dello Sviluppatore Nuxiva
          </strong>
          Segui questi 6 passaggi in sequenza per costruire un'estensione pronta all'uso, stabile, sicura e compatibile con l'intero ecosistema Nuxiva.
        </div>
      </div>

      <div className="space-y-3">
        {steps.map((step) => {
          const Icon = step.icon;
          const isExpanded = expandedStep === step.num;

          return (
            <div
              key={step.num}
              className={`rounded-2xl border transition-all ${
                isExpanded
                  ? 'border-[var(--md-sys-color-primary)] bg-[var(--md-sys-color-surface-container)] shadow-xs'
                  : 'border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface)]/60 hover:border-[var(--md-sys-color-outline)]'
              }`}
            >
              <button
                type="button"
                onClick={() => setExpandedStep(isExpanded ? 0 : step.num)}
                className="w-full flex items-center justify-between p-4 text-left gap-3"
              >
                <div className="flex items-center gap-3">
                  <div className={`p-2.5 rounded-xl ${step.bgColor} ${step.color} border ${step.borderColor} shrink-0`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-[var(--md-sys-color-on-surface)]">
                      {step.title}
                    </h4>
                    <p className="text-[11px] text-[var(--md-sys-color-on-surface-variant)] line-clamp-1 mt-0.5">
                      {step.summary}
                    </p>
                  </div>
                </div>
                <ChevronRight
                  className={`w-4 h-4 text-[var(--md-sys-color-on-surface-variant)] transition-transform shrink-0 ${
                    isExpanded ? 'rotate-90' : ''
                  }`}
                />
              </button>

              {isExpanded && (
                <div className="px-4 pb-4 pt-1 border-t border-[var(--md-sys-color-outline-variant)] space-y-3">
                  <div className="space-y-2">
                    <span className="text-[11px] font-bold text-[var(--md-sys-color-on-surface)] block">
                      Dettagli Operativi:
                    </span>
                    <ul className="space-y-1.5">
                      {step.details.map((detail, idx) => (
                        <li key={idx} className="flex items-start gap-2 text-xs text-[var(--md-sys-color-on-surface-variant)] leading-relaxed">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                          <span>{detail}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="rounded-xl bg-black/60 border border-white/10 p-3 overflow-x-auto">
                    <pre className="font-mono text-[11px] text-blue-200 leading-relaxed">
                      <code>{step.codeSnippet}</code>
                    </pre>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
