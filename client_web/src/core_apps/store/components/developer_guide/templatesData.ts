import type { GuideModuleType, CodeFileType } from './types';

export const codeTemplates: Record<GuideModuleType, Record<CodeFileType, string>> = {
  app: {
    manifest: `{
  "$schema": "https://nuxiva.org/schemas/app.manifest.json",
  "id": "solar_explorer_app",
  "name": "Solar Explorer 3D",
  "version": "1.0.0",
  "kind": "app",
  "category": "productivity",
  "author": "Indie Dev Studio",
  "tone": "dark",
  "icon": "Compass",
  "icon3d": "./icon.png",
  "window": {
    "defaultWidth": 800,
    "defaultHeight": 580,
    "minWidth": 460,
    "minHeight": 340,
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
      "category": "productivity"
    }
  },
  "capabilities": ["local_storage", "webgl2", "audio_output"],
  "options": [
    {
      "id": "orbit_speed",
      "type": "range",
      "default": 5,
      "min": 1,
      "max": 20,
      "step": 1,
      "label_key": "opt_orbit_speed_label",
      "desc_key": "opt_orbit_speed_desc"
    }
  ]
}`,
    view: `import React, { useState, useEffect } from 'react';
import { Compass, Play, RotateCcw, Volume2, Shield } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { useOSApp } from '../../app_shell/window_manager/WindowContext';

export function View() {
  const { t } = useScopedI18n('solar_explorer_app');
  const os = useOSApp();
  const [isRunning, setIsRunning] = useState(false);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!isRunning) return;
    const interval = window.setInterval(() => {
      setTick((prev) => prev + 1);
    }, 1000);
    return () => window.clearInterval(interval);
  }, [isRunning]);

  return (
    <div className="flex flex-col h-full p-5 space-y-4 bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950 text-white">
      <div className="flex items-center justify-between border-b border-white/10 pb-3">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-blue-500/20 text-blue-400 border border-blue-500/30">
            <Compass className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-sm font-bold">{t('app_name')}</h1>
            <p className="text-xs text-white/60">{t('app_description')}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setIsRunning((prev) => !prev)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-xs font-semibold shadow-xs"
          >
            <Play className="w-3.5 h-3.5" />
            <span>{isRunning ? t('btn_pause') : t('btn_start')}</span>
          </button>
          <button
            type="button"
            onClick={() => setTick(0)}
            className="p-1.5 rounded-xl bg-white/10 hover:bg-white/20 text-xs text-white"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      <div className="flex-1 flex flex-col items-center justify-center p-6 rounded-2xl bg-black/40 border border-white/10 text-center">
        <div className="text-4xl font-extrabold text-blue-400 mb-2 font-mono">
          {tick} s
        </div>
        <p className="text-xs text-white/70 max-w-sm">
          {isRunning ? t('simulation_active') : t('simulation_idle')}
        </p>
      </div>
    </div>
  );
}`,
    i18n: `{
  "meta": {
    "locale": "it"
  },
  "dictionary": {
    "app_name": "Solar Explorer 3D",
    "app_description": "Simulazione orbitale interattiva 100% autonoma",
    "btn_start": "Avvia Simulazione",
    "btn_pause": "Sospendi",
    "simulation_active": "Motore fisico orbitale in esecuzione in tempo reale.",
    "simulation_idle": "Premi Avvia per iniziare il calcolo orbitale.",
    "opt_orbit_speed_label": "Velocità di rivoluzione planetaria",
    "opt_orbit_speed_desc": "Regola il fattore di moltiplicazione del tempo"
  }
}`
  },
  engine: {
    manifest: `{
  "$schema": "https://nuxiva.org/schemas/engine.manifest.json",
  "id": "hybrid_audio_transcriber",
  "name": "Hybrid Voice Transcriber",
  "version": "1.1.0",
  "kind": "engine",
  "family": "voice_recognition",
  "author": "Speech Research Group",
  "capabilities": ["audio_stream_capture", "vad_filter", "local_weights"],
  "options": [
    {
      "id": "vad_sensitivity",
      "type": "range",
      "default": 3,
      "min": 1,
      "max": 5,
      "step": 1,
      "label_key": "opt_vad_label",
      "desc_key": "opt_vad_desc"
    }
  ]
}`,
    view: `import React, { useState } from 'react';
import { Mic, Activity, CheckCircle, Volume2 } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';

export function View() {
  const { t } = useScopedI18n('hybrid_audio_transcriber');
  const [listening, setListening] = useState(false);

  return (
    <div className="h-full p-5 space-y-4 bg-[var(--md-sys-color-surface-container)] text-[var(--md-sys-color-on-surface)]">
      <div className="flex items-center gap-3 border-b border-[var(--md-sys-color-outline-variant)] pb-3">
        <div className="p-2.5 rounded-xl bg-indigo-500/15 text-indigo-400 border border-indigo-400/30">
          <Mic className="w-5 h-5" />
        </div>
        <div>
          <h2 className="text-sm font-bold">{t('engine_title')}</h2>
          <p className="text-xs text-[var(--md-sys-color-on-surface-variant)]">{t('engine_desc')}</p>
        </div>
      </div>
      <div className="p-6 rounded-2xl bg-[var(--md-sys-color-surface)] border border-[var(--md-sys-color-outline-variant)] flex items-center justify-between">
        <div>
          <span className="text-xs font-bold block">{t('stream_status')}</span>
          <span className="text-xs text-emerald-400 flex items-center gap-1 mt-0.5">
            <CheckCircle className="w-3.5 h-3.5" />
            {t('engine_ready')}
          </span>
        </div>
        <button
          type="button"
          onClick={() => setListening((v) => !v)}
          className="px-4 py-2 rounded-xl bg-[var(--md-sys-color-primary)] text-white text-xs font-bold"
        >
          {listening ? t('btn_stop') : t('btn_listen')}
        </button>
      </div>
    </div>
  );
}`,
    i18n: `{
  "meta": {
    "locale": "it"
  },
  "dictionary": {
    "engine_title": "Hybrid Voice Transcriber",
    "engine_desc": "Motore acustico ad alta precisione con VAD",
    "stream_status": "Stato del Flusso",
    "engine_ready": "Pronto per l'elaborazione",
    "btn_listen": "Avvia Ascolto",
    "btn_stop": "Ferma",
    "opt_vad_label": "Sensibilità del Voice Activity Detector",
    "opt_vad_desc": "Filtra il rumore di fondo prima del campionamento"
  }
}`
  },
  agent: {
    manifest: `{
  "$schema": "https://nuxiva.org/schemas/agent.manifest.json",
  "id": "financial_risk_agent",
  "name": "Financial Risk Officer Agent",
  "version": "1.0.0",
  "kind": "agent",
  "role": "risk_officer",
  "author": "FinTech Alliance",
  "capabilities": ["portfolio_analytics", "stress_test", "risk_alert"],
  "options": [
    {
      "id": "volatility_threshold",
      "type": "range",
      "default": 18,
      "min": 5,
      "max": 50,
      "step": 1,
      "label_key": "opt_volatility_label",
      "desc_key": "opt_volatility_desc"
    }
  ]
}`,
    view: `import React, { useState } from 'react';
import { Bot, AlertTriangle, ShieldCheck, Play } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';

export function View() {
  const { t } = useScopedI18n('financial_risk_agent');
  const [analyzing, setAnalyzing] = useState(false);

  return (
    <div className="h-full p-5 space-y-4 bg-[var(--md-sys-color-surface-container)] text-[var(--md-sys-color-on-surface)]">
      <div className="flex items-center gap-3 border-b border-[var(--md-sys-color-outline-variant)] pb-3">
        <div className="p-2.5 rounded-xl bg-emerald-500/15 text-emerald-400 border border-emerald-400/30">
          <Bot className="w-5 h-5" />
        </div>
        <div>
          <h2 className="text-sm font-bold">{t('agent_title')}</h2>
          <p className="text-xs text-[var(--md-sys-color-on-surface-variant)]">{t('agent_desc')}</p>
        </div>
      </div>
      <div className="p-4 rounded-2xl bg-[var(--md-sys-color-surface)] border border-[var(--md-sys-color-outline-variant)] space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold">{t('portfolio_health')}</span>
          <span className="text-xs text-emerald-400 flex items-center gap-1">
            <ShieldCheck className="w-4 h-4" />
            98.4%
          </span>
        </div>
        <button
          type="button"
          onClick={() => setAnalyzing((v) => !v)}
          className="w-full py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold flex items-center justify-center gap-2"
        >
          <Play className="w-3.5 h-3.5" />
          <span>{analyzing ? t('btn_evaluating') : t('btn_run_stress_test')}</span>
        </button>
      </div>
    </div>
  );
}`,
    i18n: `{
  "meta": {
    "locale": "it"
  },
  "dictionary": {
    "agent_title": "Financial Risk Officer Agent",
    "agent_desc": "Agente cognitivo autonomo per monitoraggio volatilità",
    "portfolio_health": "Indice di Robustezza Capitale",
    "btn_run_stress_test": "Esegui Stress Test Monte Carlo",
    "btn_evaluating": "Valutazione Rischio in Corso...",
    "opt_volatility_label": "Soglia di Volatilità d'Allarme",
    "opt_volatility_desc": "Genera una notifica di sistema al superamento della percentuale"
  }
}`
  },
  plugin: {
    manifest: `{
  "$schema": "https://nuxiva.org/schemas/plugin.manifest.json",
  "id": "cpu_freq_tray_widget",
  "name": "CPU Frequency Tray Widget",
  "version": "1.0.0",
  "kind": "plugin",
  "author": "Kernel Tweaks",
  "placement": {
    "desktop": false,
    "taskbar": {
      "pinned": false,
      "tray": true,
      "tray_order": 4
    },
    "control_panel": {
      "show": true,
      "category": "sistema"
    }
  },
  "capabilities": ["telemetry_read", "tray_badge"],
  "options": [
    {
      "id": "poll_rate_seconds",
      "type": "range",
      "default": 2,
      "min": 1,
      "max": 10,
      "step": 1,
      "label_key": "opt_poll_label",
      "desc_key": "opt_poll_desc"
    }
  ]
}`,
    view: `import React, { useState } from 'react';
import { Gauge, Cpu, CheckCircle } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';

export function View() {
  const { t } = useScopedI18n('cpu_freq_tray_widget');
  const [governor, setGovernor] = useState('schedutil');

  return (
    <div className="p-4 space-y-3 bg-[var(--md-sys-color-surface-container)] text-[var(--md-sys-color-on-surface)] rounded-2xl">
      <div className="flex items-center gap-2 border-b border-[var(--md-sys-color-outline-variant)] pb-2">
        <Gauge className="w-4 h-4 text-amber-400" />
        <h3 className="text-xs font-bold">{t('widget_title')}</h3>
      </div>
      <div className="text-center py-3 bg-[var(--md-sys-color-surface)] rounded-xl border border-[var(--md-sys-color-outline-variant)]">
        <span className="text-xl font-bold font-mono text-amber-400">3.85 GHz</span>
        <span className="text-[10px] text-[var(--md-sys-color-on-surface-variant)] block mt-0.5">{t('all_cores')}</span>
      </div>
    </div>
  );
}`,
    i18n: `{
  "meta": {
    "locale": "it"
  },
  "dictionary": {
    "widget_title": "CPU Frequency Monitor",
    "all_cores": "Frequenza Media Tutti i Core",
    "opt_poll_label": "Intervallo di Campionamento (secondi)",
    "opt_poll_desc": "Frequenza di aggiornamento del badge nella barra delle applicazioni"
  }
}`
  }
};
