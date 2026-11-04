import { StoreCatalogResponse, StoreInstallResponse, StoreRepository } from './types';

export async function fetchStoreCatalog(): Promise<StoreCatalogResponse> {
  const res = await fetch('/api/store/packages', {
    credentials: 'same-origin',
    cache: 'no-store'
  });
  if (!res.ok) {
    throw new Error('fetch_catalog_failed');
  }
  return res.json();
}

export async function fetchStoreRepositories(): Promise<StoreRepository[]> {
  const res = await fetch('/api/store/repositories', {
    credentials: 'same-origin',
    cache: 'no-store'
  });
  if (!res.ok) {
    throw new Error('fetch_repositories_failed');
  }
  const data = await res.json();
  return data.repositories || [];
}

export async function addStoreRepository(payload: {
  name: string;
  url: string;
  description?: string;
  packages?: any[];
}): Promise<StoreRepository> {
  const res = await fetch('/api/store/repositories', {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      'X-Nuxiva-Request': '1'
    },
    body: JSON.stringify(payload)
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || data.error || 'add_repository_failed');
  }
  return data.repository;
}

export async function deleteStoreRepository(repoId: string): Promise<void> {
  const res = await fetch(`/api/store/repositories/${encodeURIComponent(repoId)}`, {
    method: 'DELETE',
    credentials: 'same-origin',
    headers: {
      'X-Nuxiva-Request': '1'
    }
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || data.error || 'delete_repository_failed');
  }
}

export async function installPackage(itemId: string, force: boolean = false): Promise<StoreInstallResponse> {
  const res = await fetch(`/api/store/packages/${encodeURIComponent(itemId)}/install`, {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      'X-Nuxiva-Request': '1'
    },
    body: JSON.stringify({ force })
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || data.error || 'install_failed');
  }
  return data;
}

export async function uninstallPackage(itemId: string): Promise<void> {
  const res = await fetch(`/api/store/packages/${encodeURIComponent(itemId)}/uninstall`, {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      'X-Nuxiva-Request': '1'
    }
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || data.error || 'uninstall_failed');
  }
}
