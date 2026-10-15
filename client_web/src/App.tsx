import React, { useState } from 'react';
import { NavigationTab } from './shared/types';
import { AppNavbar } from './shared/layout/AppNavbar';
import { I18nProvider } from './shared/i18n/I18nContext';
import { MeshTopologyCanvas } from './mesh_canvas';
import { GlobalCommandGrid } from './core_apps';
import { NodeDetailView } from './node_apps/NodeDetailView';
import { ArrowLeft, Layers, Network } from 'lucide-react';

// Core Apps Dynamic Components Map
import { View as UpdaterView } from './core_apps/updater/View';
import { View as NodesView } from './core_apps/nodes/View';
import { View as AgentsView } from './core_apps/agents/View';
import { View as AlgorithmsView } from './core_apps/algorithms/View';
import { View as AutomationsView } from './core_apps/automations/View';
import { View as FlowsView } from './core_apps/flows/View';
import { View as HabitsView } from './core_apps/habits/View';
import { View as HandsView } from './core_apps/hands/View';
import { View as LawsView } from './core_apps/laws/View';
import { View as MusicView } from './core_apps/music/View';
import { View as PeopleView } from './core_apps/people/View';
import { View as PlacesView } from './core_apps/places/View';
import { View as StudyView } from './core_apps/study/View';
import { View as TwinView } from './core_apps/twin/View';
import { View as VaultView } from './core_apps/vault/View';
import { View as VpnView } from './core_apps/vpn/View';
import { View as FeaturesHubView } from './core_apps/features_hub/View';
import { View as GoogleView } from './core_apps/google/View';
import { View as IptvView } from './core_apps/iptv/View';
import { View as CamerasView } from './core_apps/cameras/View';
import { View as FirewallView } from './core_apps/firewall/View';
import { View as OfficeView } from './core_apps/office/View';
import { View as EmergencyView } from './core_apps/emergency/View';
import { View as BackupView } from './core_apps/backup/View';

const CORE_APP_COMPONENTS: Record<string, React.FC> = {
  updater: UpdaterView,
  nodes: NodesView,
  agents: AgentsView,
  algorithms: AlgorithmsView,
  automations: AutomationsView,
  flows: FlowsView,
  habits: HabitsView,
  hands: HandsView,
  laws: LawsView,
  music: MusicView,
  people: PeopleView,
  places: PlacesView,
  study: StudyView,
  twin: TwinView,
  vault: VaultView,
  vpn: VpnView,
  features_hub: FeaturesHubView,
  google: GoogleView,
  iptv: IptvView,
  cameras: CamerasView,
  firewall: FirewallView,
  office: OfficeView,
  emergency: EmergencyView,
  backup: BackupView,
};

export const MainConsole: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<NavigationTab>('MESH_CANVAS');
  const [selectedNode, setSelectedNode] = useState<{
    id: string;
    name: string;
    tier: string;
    ip: string;
  } | null>(null);
  const [selectedAppId, setSelectedAppId] = useState<string | null>(null);

  const handleOpenCoreControl = () => {
    setSelectedAppId(null);
    setCurrentTab('CORE_APPS');
  };

  const handleOpenNodeControl = (node: {
    id: string;
    name: string;
    tier: string;
    ip: string;
  }) => {
    setSelectedNode(node);
    setCurrentTab('NODE_CONTROL');
  };

  const handleSelectApp = (appId: string) => {
    setSelectedAppId(appId);
    setCurrentTab('APP_VIEW');
  };

  const SelectedAppComponent = selectedAppId ? CORE_APP_COMPONENTS[selectedAppId] : null;

  return (
    <div className="min-h-screen bg-[#030712] text-slate-100 flex flex-col font-['Inter'] selection:bg-cyan-500 selection:text-slate-950 overflow-hidden">
      {/* Sleek Top Navbar with Breadcrumb */}
      <AppNavbar
        currentTab={currentTab}
        onTabChange={(tab) => {
          if (tab === 'MESH_CANVAS') {
            setSelectedAppId(null);
          }
          setCurrentTab(tab);
        }}
        isMeshConnected={true}
        selectedNodeName={selectedNode?.name}
        selectedAppName={selectedAppId ? selectedAppId.toUpperCase() : undefined}
      />

      {/* Main Dynamic Viewport */}
      <main className="flex-1 w-full flex flex-col overflow-y-auto">
        {/* Level 0: The Spatial Holographic Mesh Canvas */}
        {currentTab === 'MESH_CANVAS' && (
          <MeshTopologyCanvas
            onOpenCoreControl={handleOpenCoreControl}
            onOpenNodeControl={handleOpenNodeControl}
          />
        )}

        {/* Level 1: Central Nucleus General Control Panel (24 Core Apps A-Z) */}
        {currentTab === 'CORE_APPS' && (
          <GlobalCommandGrid
            onBackToCanvas={() => setCurrentTab('MESH_CANVAS')}
            onSelectApp={handleSelectApp}
          />
        )}

        {/* Level 1.5: Inside Specific Core App */}
        {currentTab === 'APP_VIEW' && selectedAppId && (
          <div className="flex-1 flex flex-col">
            {/* Top Sub-Navigation Bar */}
            <div className="flex items-center justify-between px-6 py-3 bg-slate-950/80 border-b border-slate-800">
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setCurrentTab('CORE_APPS')}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 hover:border-cyan-500 text-xs text-slate-300 font-mono transition"
                >
                  <ArrowLeft className="w-4 h-4" />
                  <span>Torna al Nucleo</span>
                </button>
                <div className="h-4 w-px bg-slate-800" />
                <button
                  onClick={() => setCurrentTab('MESH_CANVAS')}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 hover:border-cyan-500 text-xs text-slate-300 font-mono transition"
                >
                  <Network className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Mappa Spaziale</span>
                </button>
              </div>

              <div className="flex items-center gap-2 text-xs font-mono text-cyan-400">
                <Layers className="w-4 h-4" />
                <span className="uppercase font-bold tracking-wider">{selectedAppId}</span>
              </div>
            </div>

            {/* App View Content */}
            <div className="flex-1 overflow-y-auto">
              {SelectedAppComponent ? (
                <SelectedAppComponent />
              ) : (
                <div className="p-8 text-center text-slate-500 font-mono">
                  Applicativo '{selectedAppId}' in fase di caricamento...
                </div>
              )}
            </div>
          </div>
        )}

        {/* Level 2: Personal Node Control Panel (9 Hardware Modules) */}
        {currentTab === 'NODE_CONTROL' && selectedNode && (
          <NodeDetailView
            nodeId={selectedNode.id}
            nodeName={selectedNode.name}
            nodeTier={selectedNode.tier}
            ipAddress={selectedNode.ip}
            onBack={() => setCurrentTab('MESH_CANVAS')}
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
