import React, { useCallback, useState } from 'react';
import { GlobalCommandGrid } from '../core_apps';
import { NeuralMeshView, NeuronOpenTarget } from '../features/neural_mesh';
import { NodeDetailView } from '../node_apps/NodeDetailView';
import { AppViewFrame } from './AppViewFrame';
import { ShellNavbar } from './navbar/ShellNavbar';
import { CORE_ROUTE, MESH_ROUTE, ShellRoute } from './shellRoute';

export const AppShell: React.FC = () => {
  const [route, setRoute] = useState<ShellRoute>(MESH_ROUTE);

  const goMesh = useCallback(() => setRoute(MESH_ROUTE), []);
  const goCore = useCallback(() => setRoute(CORE_ROUTE), []);
  const openApp = useCallback((appId: string) => setRoute({ view: 'app', appId }), []);
  const openNode = useCallback((node: NeuronOpenTarget) => setRoute({ view: 'node', node }), []);
  const renameNode = useCallback((nodeId: string, name: string) => {
    setRoute((current) =>
      current.view === 'node' && current.node.id === nodeId ? { view: 'node', node: { ...current.node, name } } : current,
    );
  }, []);

  return (
    <div className="flex h-[100dvh] flex-col overflow-hidden bg-[#02040a] font-['Inter'] text-slate-100 selection:bg-cyan-400 selection:text-slate-950">
      <ShellNavbar route={route} onNavigateMesh={goMesh} onNavigateCore={goCore} />
      <main className="flex min-h-0 w-full flex-1 flex-col overflow-y-auto">
        {route.view === 'mesh' && <NeuralMeshView onOpenCore={goCore} onOpenNeuron={openNode} />}
        {route.view === 'core' && <GlobalCommandGrid onBackToCanvas={goMesh} onSelectApp={openApp} />}
        {route.view === 'app' && <AppViewFrame appId={route.appId} onBackToCore={goCore} onBackToMesh={goMesh} />}
        {route.view === 'node' && (
          <NodeDetailView
            nodeId={route.node.id}
            nodeName={route.node.name}
            nodeTier={route.node.tier}
            ipAddress={route.node.ip}
            onBack={goMesh}
            onRename={renameNode}
          />
        )}
      </main>
    </div>
  );
};
