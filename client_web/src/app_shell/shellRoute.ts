import { NeuronOpenTarget } from '../features/neural_mesh';

export type ShellRoute =
  | { readonly view: 'mesh' }
  | { readonly view: 'core' }
  | { readonly view: 'app'; readonly appId: string }
  | { readonly view: 'node'; readonly node: NeuronOpenTarget };

export const MESH_ROUTE: ShellRoute = { view: 'mesh' };
export const CORE_ROUTE: ShellRoute = { view: 'core' };
