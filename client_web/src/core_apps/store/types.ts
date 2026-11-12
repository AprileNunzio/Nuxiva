export interface StorePackage {
  id: string;
  category: string;
  title: string;
  description: string;
  size_gb: number;
  installed: boolean;
  removable: boolean;
  detect?: string;
  budget_ok?: boolean;
  source?: 'official' | 'custom';
  repository_id?: string;
  repository_name?: string;
}

export interface StoreResources {
  disk_free_gb: number;
  ram_total_gb: number;
}

export interface StoreRepository {
  id: string;
  name: string;
  url: string;
  description?: string;
  official: boolean;
  enabled: boolean;
  packages_count?: number;
}

export interface StoreCatalogResponse {
  packages: StorePackage[];
  resources: StoreResources;
  repositories?: StoreRepository[];
}

export interface StoreInstallResponse {
  ok: boolean;
  id?: string;
  applying?: boolean;
  advisory?: boolean;
  can_force?: boolean;
  message?: string;
  error?: string;
  ram_total_gb?: number;
  recommended_ram_gb?: number;
}
