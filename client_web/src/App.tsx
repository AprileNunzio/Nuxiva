import React, { useState, useEffect } from 'react';
import { NavigationTab, KnowledgeNode } from './shared/types';
import { AppNavbar } from './shared/layout/AppNavbar';
import { I18nProvider, useI18n } from './shared/i18n/I18nContext';
import { NeuralCoreCanvas } from './features/core_visualizer_3d/NeuralCoreCanvas';
import { SpatialWorldView } from './features/world_3d/SpatialWorldView';
import { Studio3DView } from './features/studio_3d/Studio3DView';
import { ControlDeckView } from './features/control_deck/ControlDeckView';

export const MainConsole: React.FC = () => {
  const { t } = useI18n();
  const [currentTab, setCurrentTab] = useState<NavigationTab>('WORLD_3D');
  const [nodes, setNodes] = useState<KnowledgeNode[]>([
    {
      id: 'nuxiva_core',
      node_type: 'AGENT',
      label: 'Nuxiva Orchestrator',
      properties: { status: 'ONLINE' },
      created_at: Date.now(),
      updated_at: Date.now()
    },
    {
      id: 'user_master',
      node_type: 'USER',
      label: 'Proprietario (Admin)',
      properties: { biometric_verified: true },
      created_at: Date.now(),
      updated_at: Date.now()
    },
    {
      id: 'home_assistant_node',
      node_type: 'DEVICE',
      label: 'Home Assistant Hub',
      properties: { domain: 'iot' },
      created_at: Date.now(),
      updated_at: Date.now()
    }
  ]);

  const fetchGraphNodes = async () => {
    try {
      const res = await fetch('/api/v1/knowledge/graph');
      if (res.ok) {
        const data = await res.json();
        if (data.graph?.nodes) {
          setNodes(data.graph.nodes);
        }
      }
    } catch {
    }
  };

  useEffect(() => {
    fetchGraphNodes();
  }, []);

  const handleSendCommand = async (command: string): Promise<string> => {
    try {
      const res = await fetch('/api/v1/command', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer v1.local.mock_token_for_browser'
        },
        body: JSON.stringify({
          query: command,
          device_id: 'web_dashboard_client'
        })
      });

      if (res.ok) {
        const payload = await res.json();
        fetchGraphNodes();
        return payload.speech_output || t('cmd_executed_default');
      }
    } catch {
    }

    const lower = command.toLowerCase();
    if (lower.includes('luci') || lower.includes('luce') || lower.includes('light')) {
      return t('cmd_ha_lights');
    }
    if (lower.includes('telecamera') || lower.includes('sicurezza') || lower.includes('camera') || lower.includes('security')) {
      return t('cmd_security_frigate');
    }
    if (lower.includes('codice') || lower.includes('programma') || lower.includes('code') || lower.includes('software')) {
      return t('cmd_sandbox_code');
    }
    return `${t('cmd_received')}: "${command}". ${t('cmd_routed')}`;
  };

  return (
    <div className="min-h-screen bg-[#030712] text-slate-100 flex flex-col font-['Inter'] selection:bg-cyan-500 selection:text-slate-950">
      <AppNavbar 
        currentTab={currentTab} 
        onTabChange={setCurrentTab} 
        isMeshConnected={true} 
      />

      <main className="flex-1 w-full flex flex-col overflow-hidden">
        {currentTab === 'CORE' && (
          <NeuralCoreCanvas 
            onSendCommand={handleSendCommand} 
            activeNodes={nodes} 
          />
        )}

        {currentTab === 'WORLD_3D' && (
          <SpatialWorldView />
        )}

        {currentTab === 'STUDIO_3D' && (
          <Studio3DView />
        )}

        {currentTab === 'CONTROL_DECK' && (
          <ControlDeckView 
            nodes={nodes} 
            onRefreshGraph={fetchGraphNodes} 
          />
        )}
      </main>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <I18nProvider>
      <MainConsole />
    </I18nProvider>
  );
};

export default App;
