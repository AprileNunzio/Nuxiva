import React, { createContext, useContext } from 'react';
import { useMeshTopology, MeshTopologyState } from '../features/neural_mesh/hooks/useMeshTopology';
const TopologyContext = createContext<MeshTopologyState | null>(null);
export function WindowTopologyProvider({ children }: { children: React.ReactNode }) {
  const topology = useMeshTopology();
  return <TopologyContext.Provider value={topology}>{children}</TopologyContext.Provider>;
}
export function useWindowTopology() {
  const topology = useContext(TopologyContext);
  if (!topology) throw new Error('Missing WindowTopologyProvider');
  return topology;
}
