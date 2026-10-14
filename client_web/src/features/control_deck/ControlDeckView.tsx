import React, { useState } from 'react';
import { 
  Cpu, 
  Database, 
  Sliders, 
  Terminal, 
  ShieldCheck, 
  Network, 
  Home, 
  Camera, 
  Code2, 
  RefreshCw,
  Server
} from 'lucide-react';
import * as monaco from 'monaco-editor';
import { Terminal as XTerm } from 'xterm';
import 'xterm/css/xterm.css';
import { AgentDescriptor, SystemModelConfig, KnowledgeNode } from '../../shared/types';
import { NeuralAnalysisFlow } from './NeuralAnalysisFlow';
import { ProjectWidget } from './ProjectWidget';
import { useI18n } from '../../shared/i18n/I18nContext';
import { CognitiveEngineSelector } from '../cognitive_engine';

interface ControlDeckViewProps {
  nodes: KnowledgeNode[];
  onRefreshGraph: () => void;
}

export const ControlDeckView: React.FC<ControlDeckViewProps> = ({ nodes, onRefreshGraph }) => {
  const { t } = useI18n();

  const [modelConfig, setModelConfig] = useState<SystemModelConfig>({
    activeProvider: 'OLLAMA',
    ollamaModel: 'qwen2.5-coder:7b',
    temperature: 0.2,
    maxTokens: 4096,
    voiceVolume: 0.9,
    voiceSpeed: 1.0,
  });

  React.useEffect(() => {
    const ws = new WebSocket('wss://localhost:8443/bus-core');
    const container = document.getElementById('monaco-container');
    let editor: monaco.editor.IStandaloneCodeEditor | null = null;
    if (container) {
      editor = monaco.editor.create(container, {
        value: '', language: 'python', theme: 'vs-dark', automaticLayout: true, minimap: { enabled: false }
      });
    }
    const term = new XTerm({ theme: { background: '#1e1e1e' }, cursorBlink: true });
    const termEl = document.getElementById('xterm-container');
    if (termEl) term.open(termEl);

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'file_sync' && editor) editor.setValue(data.content);
            if (data.type === 'term_out') term.write(data.content);
        } catch (e) {}
    };

    return () => {
        if (editor) editor.dispose();
        term.dispose();
        ws.close();
    };
  }, []);

  const agents: AgentDescriptor[] = [
    {
      id: 'agent_home_assistant',
      name: t('deck_agent_home'),
      status: 'IDLE',
      capabilities: [t('deck_cap_lights'), t('deck_cap_climate'), t('deck_cap_shutters'), t('deck_cap_sensors')],
      latencyMs: 14
    },
    {
      id: 'agent_vision_surveillance',
      name: t('deck_agent_vision'),
      status: 'EXECUTING',
      capabilities: [t('deck_cap_rtsp'), t('deck_cap_faces'), t('deck_cap_perimeter')],
      latencyMs: 28
    },
    {
      id: 'agent_self_healing_coder',
      name: t('deck_agent_coder'),
      status: 'IDLE',
      capabilities: [t('deck_cap_ast'), t('deck_cap_sandbox'), t('deck_cap_hotpatch')],
      latencyMs: 110
    }
  ];

  return (
    <div className="w-full max-w-7xl 3xl:max-w-[1800px] 4xl:max-w-[2400px] 5xl:max-w-[3600px] 8k:max-w-[7200px] mx-auto px-3 sm:px-6 8k:px-16 py-4 sm:py-8 8k:py-16 space-y-6 sm:space-y-8 8k:space-y-12">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-3xl 8k:text-5xl font-['Rajdhani'] font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-blue-400 to-indigo-400">
            {t('deck_title')}
          </h1>
          <p className="text-xs sm:text-sm 8k:text-xl text-slate-400 mt-1">
            {t('deck_subtitle')}
          </p>
        </div>
        <CognitiveEngineSelector />
      </div>


      <div className="grid grid-cols-1 lg:grid-cols-3 4xl:grid-cols-4 8k:grid-cols-6 gap-5 sm:gap-6 8k:gap-10">
        <div className="lg:col-span-2 4xl:col-span-3 8k:col-span-4 space-y-5 sm:space-y-6 8k:space-y-10">
          {/* Agent pool */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl 8k:rounded-3xl p-4 sm:p-5 8k:p-8 backdrop-blur-md">
            <div className="flex items-center justify-between mb-4 8k:mb-6">
              <div className="flex items-center space-x-2.5 8k:space-x-4">
                <Cpu className="w-5 h-5 8k:w-8 8k:h-8 text-cyan-400" />
                <h2 className="font-['Rajdhani'] text-base sm:text-lg 8k:text-2xl font-semibold text-slate-100">
                  {t('deck_agents_pool')}
                </h2>
              </div>
              <span className="text-xs 8k:text-base font-mono text-cyan-400 bg-cyan-950/60 border border-cyan-800/60 px-2.5 py-1 rounded-full">
                {agents.length} {t('deck_agents_operational')}
              </span>
            </div>

            <div className="space-y-3 8k:space-y-5">
              {agents.map((agent) => (
                <div 
                  key={agent.id}
                  className="bg-slate-950/50 border border-slate-800/80 hover:border-cyan-500/40 p-3.5 sm:p-4 8k:p-6 rounded-xl 8k:rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 transition-all"
                >
                  <div className="flex items-start space-x-3 8k:space-x-5">
                    <div className="p-2 8k:p-3 rounded-lg 8k:rounded-xl bg-slate-900 border border-slate-800 text-cyan-400 mt-0.5 shrink-0">
                      {agent.id.includes('home') && <Home className="w-4 h-4 8k:w-7 8k:h-7" />}
                      {agent.id.includes('vision') && <Camera className="w-4 h-4 8k:w-7 8k:h-7" />}
                      {agent.id.includes('coder') && <Code2 className="w-4 h-4 8k:w-7 8k:h-7" />}
                    </div>
                    <div>
                      <h3 className="text-xs sm:text-sm 8k:text-xl font-semibold text-slate-200">{agent.name}</h3>
                      <div className="flex flex-wrap gap-1.5 8k:gap-2.5 mt-1.5">
                        {agent.capabilities.map((cap) => (
                          <span key={cap} className="text-[10px] sm:text-xs 8k:text-sm bg-slate-800/80 text-slate-400 px-2 py-0.5 rounded">
                            {cap}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center space-x-3 8k:space-x-5 self-end sm:self-center">
                    <span className="text-xs 8k:text-base font-mono text-slate-400">{agent.latencyMs}ms</span>
                    <span className={`text-[10px] 8k:text-sm font-mono px-2 py-0.5 rounded-full ${
                      agent.status === 'EXECUTING' 
                        ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30 animate-pulse'
                        : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                    }`}>
                      {agent.status === 'EXECUTING' ? t('status_executing') : t('status_idle')}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Knowledge graph database */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl 8k:rounded-3xl p-4 sm:p-5 8k:p-8 backdrop-blur-md">
            <div className="flex items-center justify-between mb-4 8k:mb-6">
              <div className="flex items-center space-x-2.5 8k:space-x-4">
                <Database className="w-5 h-5 8k:w-8 8k:h-8 text-blue-400" />
                <h2 className="font-['Rajdhani'] text-base sm:text-lg 8k:text-2xl font-semibold text-slate-100">
                  {t('deck_database_title')}
                </h2>
              </div>
              <button 
                onClick={onRefreshGraph}
                className="flex items-center space-x-1.5 8k:space-x-3 text-xs 8k:text-base text-cyan-400 hover:text-cyan-300 bg-cyan-950/40 hover:bg-cyan-900/40 border border-cyan-800/50 px-3 py-1.5 8k:px-5 8k:py-2.5 rounded-lg 8k:rounded-xl transition-all"
              >
                <RefreshCw className="w-3.5 h-3.5 8k:w-5 8k:h-5" />
                <span>{t('deck_refresh_nodes')}</span>
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 4xl:grid-cols-3 gap-3 8k:gap-5 max-h-64 8k:max-h-96 overflow-y-auto pr-1">
              {nodes.map((node) => (
                <div key={node.id} className="bg-slate-950/60 border border-slate-800 p-3 8k:p-5 rounded-xl 8k:rounded-2xl flex items-start space-x-3 8k:space-x-4">
                  <div className="p-2 8k:p-3 rounded-lg 8k:rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 shrink-0">
                    <Network className="w-4 h-4 8k:w-6 8k:h-6" />
                  </div>
                  <div className="overflow-hidden min-w-0">
                    <div className="text-xs 8k:text-base font-semibold text-slate-200 truncate">{node.label}</div>
                    <div className="text-[10px] 8k:text-sm font-mono text-cyan-400 uppercase mt-0.5">{node.node_type}</div>
                    <div className="text-[10px] 8k:text-sm text-slate-500 font-mono mt-1 truncate">ID: {node.id}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right column: Config & Terminal */}
        <div className="space-y-5 sm:space-y-6 8k:space-y-10">
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl 8k:rounded-3xl p-4 sm:p-5 8k:p-8 backdrop-blur-md space-y-4 sm:space-y-5 8k:space-y-8">
            <div className="flex items-center space-x-2.5 8k:space-x-4">
              <Sliders className="w-5 h-5 8k:w-8 8k:h-8 text-indigo-400" />
              <h2 className="font-['Rajdhani'] text-base sm:text-lg 8k:text-2xl font-semibold text-slate-100">
                {t('deck_models_config')}
              </h2>
            </div>

            <div className="space-y-3.5 sm:space-y-4 8k:space-y-6">
              <div>
                <label className="block text-xs 8k:text-base font-mono uppercase text-slate-400 mb-1.5">
                  {t('deck_primary_provider')}
                </label>
                <div className="grid grid-cols-2 gap-2 8k:gap-4">
                  {(['OLLAMA', 'OPENAI', 'ANTHROPIC', 'GEMINI'] as const).map((prov) => (
                    <button
                      key={prov}
                      onClick={() => setModelConfig({ ...modelConfig, activeProvider: prov })}
                      className={`text-xs 8k:text-base py-2 8k:py-3.5 px-3 8k:px-5 rounded-lg 8k:rounded-xl border font-mono transition-all ${
                        modelConfig.activeProvider === prov
                          ? 'bg-cyan-500/20 border-cyan-400 text-cyan-300 font-bold'
                          : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700'
                      }`}
                    >
                      {prov}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs 8k:text-base font-mono uppercase text-slate-400 mb-1.5">
                  {t('deck_local_model')}
                </label>
                <input
                  type="text"
                  value={modelConfig.ollamaModel}
                  onChange={(e) => setModelConfig({ ...modelConfig, ollamaModel: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl 8k:rounded-2xl px-3 py-2 8k:px-5 8k:py-3.5 text-xs 8k:text-base font-mono text-slate-200 focus:border-cyan-400 outline-none"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs 8k:text-base font-mono text-slate-400 mb-1">
                  <span>{t('deck_temperature')}</span>
                  <span className="text-cyan-400">{modelConfig.temperature}</span>
                </div>
                <input
                  type="range"
                  min="0.0"
                  max="1.0"
                  step="0.05"
                  value={modelConfig.temperature}
                  onChange={(e) => setModelConfig({ ...modelConfig, temperature: parseFloat(e.target.value) })}
                  className="w-full accent-cyan-400 bg-slate-800"
                />
              </div>
            </div>
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl 8k:rounded-3xl p-4 sm:p-5 8k:p-8 backdrop-blur-md">
            <div className="flex items-center space-x-2.5 8k:space-x-4 mb-3 8k:mb-5">
              <Terminal className="w-5 h-5 8k:w-8 8k:h-8 text-emerald-400" />
              <h2 className="font-['Rajdhani'] text-base sm:text-lg 8k:text-2xl font-semibold text-slate-100">
                {t('deck_terminal_title')}
              </h2>
            </div>
            <div className="flex flex-col gap-3 sm:gap-4 h-64 8k:h-96">
              <div className="flex-1 bg-black/80 rounded-xl 8k:rounded-2xl border border-slate-800 overflow-hidden" id="monaco-container"></div>
              <div className="flex-1 bg-black/80 rounded-xl 8k:rounded-2xl border border-slate-800 overflow-hidden p-2" id="xterm-container"></div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Neural Telemetry Flow Section */}
      <div className="mt-6 8k:mt-12">
        <NeuralAnalysisFlow />
      </div>
      
      {/* Floating Project Mode Widget */}
      <ProjectWidget />
    </div>
  );
};
