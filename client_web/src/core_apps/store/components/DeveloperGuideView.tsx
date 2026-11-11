import React, { useState } from 'react';
import {
  Code2,
  Terminal,
  FolderTree,
  Sparkles,
  ShieldCheck,
  Globe2,
  Check,
  Copy,
  Layers,
  Cpu,
  Bot,
  Wrench,
  Boxes
} from 'lucide-react';

interface DeveloperGuideViewProps {
  t: (key: string, params?: Record<string, any>) => string;
}

type GuideTab = 'app' | 'engine' | 'agent' | 'plugin';

export const DeveloperGuideView: React.FC<DeveloperGuideViewProps> = ({ t }) => {
  const [activeGuideTab, setActiveGuideTab] = useState<GuideTab>('app');
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => {
      setCopiedKey(null);
    }, 2000);
  };

  const appTemplate = `{
  "$schema": "https://nuxiva.org/schemas/app.manifest.json",
  "id": "il_mio_gioco",
  "name": "Il Mio Gioco 3D",
  "version": "1.0.0",
  "kind": "app",
  "category": "giochi",
  "author": "Autore Indipendente",
  "icon": "Gamepad2",
  "icon3d": "./icon.png",
  "window": {
    "width": 900,
    "height": 620,
    "resizable": true
  },
  "placement": {
    "desktop": true,
    "taskbar": {
      "pinned": false,
      "tray": false
    },
    "control_panel": {
      "show": true,
      "category": "giochi"
    }
  },
  "capabilities": ["local_storage", "webgl2", "audio_output"],
  "options": [
    {
      "id": "shadow_quality_ultra",
      "type": "boolean",
      "default": true,
      "label_key": "opt_shadows_label",
      "desc_key": "opt_shadows_desc"
    }
  ]
}`;

  const engineTemplate = `{
  "$schema": "https://nuxiva.org/schemas/engine.manifest.json",
  "id": "neural_reasoner_v2",
  "name": "Monte Carlo Tree Search Reasoner",
  "version": "2.0.0",
  "kind": "engine",
  "family": "reasoning",
  "author": "AI Research Lab",
  "capabilities": ["tree_search", "branch_pruning", "offline_eval"],
  "options": [
    {
      "id": "exploration_constant",
      "type": "range",
      "default": 14,
      "min": 1,
      "max": 30,
      "step": 1,
      "label_key": "opt_c_param_label",
      "desc_key": "opt_c_param_desc"
    }
  ]
}`;

  const agentTemplate = `{
  "$schema": "https://nuxiva.org/schemas/agent.manifest.json",
  "id": "autonomous_marketer",
  "name": "Autonomous Market Analyst",
  "version": "1.0.0",
  "kind": "agent",
  "role": "market_analyst",
  "author": "Community Developer",
  "capabilities": ["trend_scraping", "sentiment_scoring", "executive_brief"],
  "options": [
    {
      "id": "proactive_alerts",
      "type": "boolean",
      "default": true,
      "label_key": "opt_alerts_label",
      "desc_key": "opt_alerts_desc"
    }
  ]
}`;

  const pluginTemplate = `{
  "$schema": "https://nuxiva.org/schemas/plugin.manifest.json",
  "id": "crypto_ticker_tray",
  "name": "Live Crypto Ticker",
  "version": "1.0.0",
  "kind": "plugin",
  "author": "FinTech Lab",
  "placement": {
    "desktop": false,
    "taskbar": {
      "pinned": false,
      "tray": true,
      "tray_order": 5
    },
    "control_panel": {
      "show": true,
      "category": "sistema"
    }
  },
  "capabilities": ["network_fetch", "tray_badge"],
  "options": [
    {
      "id": "refresh_seconds",
      "type": "range",
      "default": 10,
      "min": 2,
      "max": 60,
      "step": 1,
      "label_key": "opt_refresh_label",
      "desc_key": "opt_refresh_desc"
    }
  ]
}`;

  const currentTemplate =
    activeGuideTab === 'app'
      ? appTemplate
      : activeGuideTab === 'engine'
      ? engineTemplate
      : activeGuideTab === 'agent'
      ? agentTemplate
      : pluginTemplate;

  const currentPath =
    activeGuideTab === 'app'
      ? 'client_web/src/apps/il_mio_gioco/'
      : activeGuideTab === 'engine'
      ? 'client_web/src/engines/reasoning/neural_reasoner_v2/'
      : activeGuideTab === 'agent'
      ? 'client_web/src/agents/autonomous_marketer/'
      : 'client_web/src/plugins/crypto_ticker_tray/';

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6">
      <div className="rounded-3xl border border-[var(--md-sys-color-outline-variant)] bg-gradient-to-br from-indigo-950/30 via-[var(--md-sys-color-surface-container)] to-blue-950/20 p-6 shadow-sm">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2.5 rounded-2xl bg-blue-500/15 text-blue-400 border border-blue-400/30">
            <Terminal className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-[var(--md-sys-color-on-surface)]">
              {t('dev_guide_title')}
            </h2>
            <p className="text-xs text-[var(--md-sys-color-on-surface-variant)] leading-relaxed">
              {t('dev_guide_subtitle')}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5 mt-5">
          <div className="p-3.5 rounded-2xl bg-[var(--md-sys-color-surface)]/60 border border-[var(--md-sys-color-outline-variant)]">
            <div className="flex items-center gap-2 mb-1.5 text-blue-400 font-bold text-xs">
              <Sparkles className="w-4 h-4 shrink-0" />
              <span>{t('dev_pillar_zero_code')}</span>
            </div>
            <p className="text-[11px] text-[var(--md-sys-color-on-surface-variant)] leading-relaxed">
              {t('dev_pillar_zero_code_desc')}
            </p>
          </div>

          <div className="p-3.5 rounded-2xl bg-[var(--md-sys-color-surface)]/60 border border-[var(--md-sys-color-outline-variant)]">
            <div className="flex items-center gap-2 mb-1.5 text-indigo-400 font-bold text-xs">
              <FolderTree className="w-4 h-4 shrink-0" />
              <span>{t('dev_pillar_manifest')}</span>
            </div>
            <p className="text-[11px] text-[var(--md-sys-color-on-surface-variant)] leading-relaxed">
              {t('dev_pillar_manifest_desc')}
            </p>
          </div>

          <div className="p-3.5 rounded-2xl bg-[var(--md-sys-color-surface)]/60 border border-[var(--md-sys-color-outline-variant)]">
            <div className="flex items-center gap-2 mb-1.5 text-emerald-400 font-bold text-xs">
              <ShieldCheck className="w-4 h-4 shrink-0" />
              <span>{t('dev_pillar_zerotrust')}</span>
            </div>
            <p className="text-[11px] text-[var(--md-sys-color-on-surface-variant)] leading-relaxed">
              {t('dev_pillar_zerotrust_desc')}
            </p>
          </div>

          <div className="p-3.5 rounded-2xl bg-[var(--md-sys-color-surface)]/60 border border-[var(--md-sys-color-outline-variant)]">
            <div className="flex items-center gap-2 mb-1.5 text-amber-400 font-bold text-xs">
              <Globe2 className="w-4 h-4 shrink-0" />
              <span>{t('dev_pillar_distribution')}</span>
            </div>
            <p className="text-[11px] text-[var(--md-sys-color-on-surface-variant)] leading-relaxed">
              {t('dev_pillar_distribution_desc')}
            </p>
          </div>
        </div>
      </div>

      <div className="rounded-3xl border border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container)] p-6 shadow-xs space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--md-sys-color-outline-variant)] pb-4">
          <div className="flex items-center gap-2">
            <Boxes className="w-5 h-5 text-[var(--md-sys-color-primary)]" />
            <h3 className="text-sm font-bold text-[var(--md-sys-color-on-surface)]">
              Template di Struttura & Manifest Indipendente
            </h3>
          </div>

          <div className="flex items-center p-1 bg-[var(--md-sys-color-surface)] rounded-xl border border-[var(--md-sys-color-outline-variant)] text-xs font-semibold">
            <button
              type="button"
              onClick={() => setActiveGuideTab('app')}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-lg transition-all ${
                activeGuideTab === 'app'
                  ? 'bg-[var(--md-sys-color-primary)] text-white shadow-xs font-bold'
                  : 'text-[var(--md-sys-color-on-surface-variant)]'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>{t('dev_tab_app')}</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveGuideTab('engine')}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-lg transition-all ${
                activeGuideTab === 'engine'
                  ? 'bg-[var(--md-sys-color-primary)] text-white shadow-xs font-bold'
                  : 'text-[var(--md-sys-color-on-surface-variant)]'
              }`}
            >
              <Cpu className="w-3.5 h-3.5" />
              <span>{t('dev_tab_engine')}</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveGuideTab('agent')}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-lg transition-all ${
                activeGuideTab === 'agent'
                  ? 'bg-[var(--md-sys-color-primary)] text-white shadow-xs font-bold'
                  : 'text-[var(--md-sys-color-on-surface-variant)]'
              }`}
            >
              <Bot className="w-3.5 h-3.5" />
              <span>{t('dev_tab_agent')}</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveGuideTab('plugin')}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-lg transition-all ${
                activeGuideTab === 'plugin'
                  ? 'bg-[var(--md-sys-color-primary)] text-white shadow-xs font-bold'
                  : 'text-[var(--md-sys-color-on-surface-variant)]'
              }`}
            >
              <Wrench className="w-3.5 h-3.5" />
              <span>{t('dev_tab_plugin')}</span>
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="space-y-3">
            <div className="rounded-2xl bg-[var(--md-sys-color-surface)] p-4 border border-[var(--md-sys-color-outline-variant)] space-y-2.5">
              <h4 className="text-xs font-bold text-[var(--md-sys-color-on-surface)] flex items-center gap-1.5">
                <FolderTree className="w-4 h-4 text-blue-400" />
                <span>Struttura della Directory</span>
              </h4>
              <div className="font-mono text-[11px] bg-black/40 rounded-xl p-3 text-emerald-300 leading-relaxed border border-white/5 overflow-x-auto">
                <div className="text-white/60">{currentPath}</div>
                <div>├── manifest.json</div>
                <div>├── View.tsx</div>
                <div>├── icon.png</div>
                <div>└── language/</div>
                <div>    ├── it.json</div>
                <div>    ├── en.json</div>
                <div>    ├── es.json</div>
                <div>    └── fr.json</div>
              </div>
            </div>

            <div className="rounded-2xl bg-[var(--md-sys-color-surface)] p-4 border border-[var(--md-sys-color-outline-variant)] space-y-2">
              <h4 className="text-xs font-bold text-[var(--md-sys-color-on-surface)] flex items-center gap-1.5">
                <Code2 className="w-4 h-4 text-indigo-400" />
                <span>Linee Guida per gli Sviluppatori</span>
              </h4>
              <ul className="text-[11px] text-[var(--md-sys-color-on-surface-variant)] space-y-1.5 list-disc pl-4 leading-relaxed">
                <li>Non inserire commenti nel codice di produzione.</li>
                <li>Mantieni ogni file rigorosamente sotto le 500 righe.</li>
                <li>Tutti i testi devono usare i18n su 4 lingue simmetriche.</li>
                <li>Richiedi solo i permessi strettamente indispensabili.</li>
              </ul>
            </div>
          </div>

          <div className="lg:col-span-2 rounded-2xl bg-black/60 border border-[var(--md-sys-color-outline-variant)] p-4 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-2 mb-2 border-b border-white/10">
                <span className="font-mono text-[11px] text-white/70">manifest.json</span>
                <button
                  type="button"
                  onClick={() => copyToClipboard(currentTemplate, 'manifest')}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold bg-white/10 hover:bg-white/20 text-white transition-all"
                >
                  {copiedKey === 'manifest' ? (
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
                <code>{currentTemplate}</code>
              </pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
