import { useScopedI18n } from '../../shared/i18n/useScopedI18n';

export const NEURAL_MESH_SCOPE = 'features/neural_mesh';

export function useMeshI18n() {
  return useScopedI18n(NEURAL_MESH_SCOPE);
}
