import { FeatureRow, FeaturesOverview } from './featureTypes';
import { Resource, useResource } from './useResource';

export interface FeatureResource {
  readonly feature: FeatureRow | null;
  readonly error: boolean;
  readonly loading: boolean;
  readonly reload: () => void;
}

export function useFeature(id: string, intervalMs = 10000): FeatureResource {
  const { data, error, loading, reload }: Resource<FeaturesOverview> = useResource<FeaturesOverview>('/api/features', intervalMs);
  return { feature: data?.features.find((item) => item.id === id) ?? null, error, loading, reload };
}
