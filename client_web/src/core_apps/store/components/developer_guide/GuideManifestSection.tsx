import React, { useState } from 'react';
import {
  FileJson,
  Layers,
  Cpu,
  Bot,
  Wrench,
  Check,
  Copy,
  Sliders,
  Maximize,
  Compass,
  Lock
} from 'lucide-react';
import type { DeveloperGuideProps, GuideModuleType } from './types';

export const GuideManifestSection: React.FC<DeveloperGuideProps> = ({ t }) => {
  const [selectedModule, setSelectedModule] = useState<GuideModuleType>('app');
  const [copied, setCopied] = useState<boolean>(false);

  const copyManifest = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const manifestSchemas: Record<GuideModuleType, string> = {
    app: `{
  "$schema": "https://nuxiva.org/schemas/app.manifest.json",
  "id": "antigravity_chess_3d",
  "name": "Antigravity Chess 3D",
  "version": "1.0.0",
  "kind": "app",
  "category": "giochi",
  "author": "Community Studio",
  "tone": "dark",
  "icon": "Gamepad2",
  "icon3d": "./icon.png",
  "window": {
    "defaultWidth": 850,
    "defaultHeight": 640,
    "minWidth": 480,
    "minHeight": 360,
    "resizable": true,
    "maximizable": true
  },
  "placement": {
    "desktop": true,
    "taskbar": {
      "pinned": true,
      "tray": false
    },
    "control_panel": {
      "show": true,
      "category": "giochi"
    }
  },
  "capabilities": [
    "local_storage",
    "webgl2",
    "audio_output"
  ],
  "options": [
    {
      "id": "shadow_quality",
      "type": "select",
      "default": "high",
      "options": ["low", "medium", "high", "ultra"],
      "label_key": "opt_shadow_label",
      "desc_key": "opt_shadow_desc"
    },
    {
      "id": "enable_sfx",
      "type": "boolean",
      "default": true,
      "label_key": "opt_sfx_label",
      "desc_key": "opt_sfx_desc"
    }
  ]
}`,
    engine: `{
  "$schema": "https://nuxiva.org/schemas/engine.manifest.json",
  "id": "neural_reasoner_pro",
  "name": "Neural Reasoner Pro",
  "version": "2.4.0",
  "kind": "engine",
  "family": "reasoning",
  "author": "Cognitive Lab",
  "capabilities": [
    "tree_search",
    "branch_pruning",
    "offline_weights"
  ],
  "options": [
    {
      "id": "max_search_depth",
      "type": "range",
      "default": 16,
      "min": 4,
      "max": 64,
      "step": 2,
      "label_key": "opt_depth_label",
      "desc_key": "opt_depth_desc"
    },
    {
      "id": "heuristic_mode",
      "type": "select",
      "default": "balanced",
      "options": ["fast", "balanced", "exhaustive"],
      "label_key": "opt_heuristic_label",
      "desc_key": "opt_heuristic_desc"
    }
  ]
}`,
    agent: `{
  "$schema": "https://nuxiva.org/schemas/agent.manifest.json",
  "id": "code_auditor_agent",
  "name": "Zero-Trust Code Auditor",
  "version": "1.2.0",
  "kind": "agent",
  "role": "security_auditor",
  "author": "CyberSec Global",
  "capabilities": [
    "ast_parsing",
    "vulnerability_scan",
    "audit_logging"
  ],
  "options": [
    {
      "id": "strict_linting",
      "type": "boolean",
      "default": true,
      "label_key": "opt_strict_label",
      "desc_key": "opt_strict_desc"
    },
    {
      "id": "scan_interval_min",
      "type": "range",
      "default": 15,
      "min": 5,
      "max": 120,
      "step": 5,
      "label_key": "opt_interval_label",
      "desc_key": "opt_interval_desc"
    }
  ]
}`,
    plugin: `{
  "$schema": "https://nuxiva.org/schemas/plugin.manifest.json",
  "id": "hardware_thermals_tray",
  "name": "Hardware Thermals Monitor",
  "version": "1.0.0",
  "kind": "plugin",
  "author": "Hardware Community",
  "placement": {
    "desktop": false,
    "taskbar": {
      "pinned": false,
      "tray": true,
      "tray_order": 3
    },
    "control_panel": {
      "show": true,
      "category": "sistema"
    }
  },
  "capabilities": [
    "system_telemetry",
    "tray_badge"
  ],
  "options": [
    {
      "id": "temperature_unit",
      "type": "select",
      "default": "celsius",
      "options": ["celsius", "fahrenheit"],
      "label_key": "opt_temp_unit_label",
      "desc_key": "opt_temp_unit_desc"
    },
    {
      "id": "high_temp_alert",
      "type": "boolean",
      "default": true,
      "label_key": "opt_alert_label",
      "desc_key": "opt_alert_desc"
    }
  ]
}`
  };

  const currentManifest = manifestSchemas[selectedModule];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 cq-md:grid-cols-3 gap-4">
        <div className="p-4 rounded-2xl bg-[var(--md-sys-color-surface-container)] border border-[var(--md-sys-color-outline-variant)] space-y-2">
          <div className="flex items-center gap-2 text-indigo-400 font-bold text-xs">
            <Compass className="w-4 h-4" />
            <span>Placement Universale</span>
          </div>
          <p className="text-[11px] text-[var(--md-sys-color-on-surface-variant)] leading-relaxed">
            Dichiara se posizionare il lanciatore sul desktop, la finestra nella taskbar, o il widget direttamente nella tray accanto all'orologio di sistema.
          </p>
        </div>

        <div className="p-4 rounded-2xl bg-[var(--md-sys-color-surface-container)] border border-[var(--md-sys-color-outline-variant)] space-y-2">
          <div className="flex items-center gap-2 text-amber-400 font-bold text-xs">
            <Sliders className="w-4 h-4" />
            <span>Autocreazione Opzioni</span>
          </div>
          <p className="text-[11px] text-[var(--md-sys-color-on-surface-variant)] leading-relaxed">
            Nessun file impostazioni da toccare: dichiara l'array `options` e Nuxiva creerà switch e slider sincronizzati in tempo reale.
          </p>
        </div>

        <div className="p-4 rounded-2xl bg-[var(--md-sys-color-surface-container)] border border-[var(--md-sys-color-outline-variant)] space-y-2">
          <div className="flex items-center gap-2 text-emerald-400 font-bold text-xs">
            <Lock className="w-4 h-4" />
            <span>Permessi Zero-Trust</span>
          </div>
          <p className="text-[11px] text-[var(--md-sys-color-on-surface-variant)] leading-relaxed">
            Dichiara esplicitamente le `capabilities` richieste. Il kernel nega ogni accesso a risorse non dichiarate preventivamente.
          </p>
        </div>
      </div>

      <div className="rounded-3xl border border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container)] p-6 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--md-sys-color-outline-variant)] pb-4">
          <div className="flex items-center gap-2">
            <FileJson className="w-5 h-5 text-[var(--md-sys-color-primary)]" />
            <h3 className="text-sm font-bold text-[var(--md-sys-color-on-surface)]">
              Specifiche Complete del `manifest.json`
            </h3>
          </div>

          <div className="flex items-center p-1 bg-[var(--md-sys-color-surface)] rounded-xl border border-[var(--md-sys-color-outline-variant)] text-xs font-semibold">
            <button
              type="button"
              onClick={() => setSelectedModule('app')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
                selectedModule === 'app'
                  ? 'bg-[var(--md-sys-color-primary)] text-white shadow-xs font-bold'
                  : 'text-[var(--md-sys-color-on-surface-variant)]'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>{t('dev_tab_app')}</span>
            </button>

            <button
              type="button"
              onClick={() => setSelectedModule('engine')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
                selectedModule === 'engine'
                  ? 'bg-[var(--md-sys-color-primary)] text-white shadow-xs font-bold'
                  : 'text-[var(--md-sys-color-on-surface-variant)]'
              }`}
            >
              <Cpu className="w-3.5 h-3.5" />
              <span>{t('dev_tab_engine')}</span>
            </button>

            <button
              type="button"
              onClick={() => setSelectedModule('agent')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
                selectedModule === 'agent'
                  ? 'bg-[var(--md-sys-color-primary)] text-white shadow-xs font-bold'
                  : 'text-[var(--md-sys-color-on-surface-variant)]'
              }`}
            >
              <Bot className="w-3.5 h-3.5" />
              <span>{t('dev_tab_agent')}</span>
            </button>

            <button
              type="button"
              onClick={() => setSelectedModule('plugin')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
                selectedModule === 'plugin'
                  ? 'bg-[var(--md-sys-color-primary)] text-white shadow-xs font-bold'
                  : 'text-[var(--md-sys-color-on-surface-variant)]'
              }`}
            >
              <Wrench className="w-3.5 h-3.5" />
              <span>{t('dev_tab_plugin')}</span>
            </button>
          </div>
        </div>

        <div className="rounded-2xl bg-black/60 border border-[var(--md-sys-color-outline-variant)] p-4 space-y-2">
          <div className="flex items-center justify-between pb-2 border-b border-white/10">
            <span className="font-mono text-xs text-blue-300">manifest.json ({selectedModule})</span>
            <button
              type="button"
              onClick={() => copyManifest(currentManifest)}
              className="flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold bg-white/10 hover:bg-white/20 text-white transition-all"
            >
              {copied ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="text-emerald-400">{t('dev_copied')}</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  <span>{t('dev_copy_template')}</span>
                </>
              )}
            </button>
          </div>
          <pre className="font-mono text-[11px] text-blue-200 overflow-x-auto p-2 leading-relaxed max-h-96">
            <code>{currentManifest}</code>
          </pre>
        </div>
      </div>
    </div>
  );
};
