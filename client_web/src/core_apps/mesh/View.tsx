import React from 'react';
import { NeuralMeshView } from '../../features/neural_mesh';
export const View: React.FC = () => <NeuralMeshView
  onOpenCore={() => window.NuxivaOS.openWindow({ appId: 'features_hub' })}
  onOpenNeuron={node => window.NuxivaOS.openWindow({ appId: 'node_apps/console', targetNodeId: node.id, initialPayload: { name: node.name } })}
/>;
