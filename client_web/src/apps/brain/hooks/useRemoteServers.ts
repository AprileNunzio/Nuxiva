import { useState } from 'react';
import { RemoteOllamaServer } from '../types';
import { DEFAULT_REMOTE_SERVERS, normalizeOllamaUrl, fetchOllamaModels } from '../defaults';

export const useRemoteServers = (
  persistState: (patch: { servers: RemoteOllamaServer[] }) => void,
  showToast: (msg: string) => void,
  t: (key: string) => string
) => {
  const [remoteServers, setRemoteServers] =
    useState<readonly RemoteOllamaServer[]>(DEFAULT_REMOTE_SERVERS);

  const saveRemoteServers = (servers: readonly RemoteOllamaServer[]) => {
    setRemoteServers(servers);
    persistState({ servers: servers as RemoteOllamaServer[] });
  };

  const handleAddRemoteServer = async (rawHost: string, label?: string) => {
    const normalized = normalizeOllamaUrl(rawHost);
    const existing = remoteServers.find((s) => s.normalizedBaseUrl === normalized);
    if (existing) {
      showToast(t('server_already_exists'));
      return;
    }
    const id = `remote_${Date.now()}`;
    const draft: RemoteOllamaServer = {
      id,
      label: label?.trim() || rawHost.trim(),
      rawInputHost: rawHost,
      normalizedBaseUrl: normalized,
      status: 'checking',
      latencyMs: null,
      lastCheckedAt: new Date().toISOString(),
      availableModels: [],
      selectedModel: '',
      errorMessage: null,
    };
    const nextList = [...remoteServers, draft];
    saveRemoteServers(nextList);
    await handleReloadRemoteModels(id, normalized);
  };

  const handleRemoveRemoteServer = (id: string) => {
    const nextList = remoteServers.filter((s) => s.id !== id);
    saveRemoteServers(nextList);
    showToast(t('server_removed'));
  };

  const handleReloadRemoteModels = async (id: string, customUrl?: string) => {
    const srv = remoteServers.find((s) => s.id === id);
    const url = customUrl || srv?.normalizedBaseUrl || '';
    if (!url) return;

    setRemoteServers((prev) =>
      prev.map((s) => (s.id === id ? { ...s, status: 'checking', errorMessage: null } : s))
    );
    try {
      const start = performance.now();
      const res = await fetchOllamaModels(url);
      const latencyMs = Math.round(performance.now() - start);
      setRemoteServers((prev) => {
        const next = prev.map((s) =>
          s.id === id
            ? {
                ...s,
                status: 'online' as const,
                latencyMs,
                lastCheckedAt: new Date().toISOString(),
                availableModels: res.models,
                selectedModel: s.selectedModel || res.models[0]?.name || '',
                errorMessage: null,
              }
            : s
        );
        persistState({ servers: next as RemoteOllamaServer[] });
        return next;
      });
      showToast(`${t('connected_success')} (${res.models.length} modelli)`);
    } catch {
      setRemoteServers((prev) => {
        const next = prev.map((s) =>
          s.id === id
            ? {
                ...s,
                status: 'offline' as const,
                errorMessage: 'Host irraggiungibile',
                lastCheckedAt: new Date().toISOString(),
              }
            : s
        );
        persistState({ servers: next as RemoteOllamaServer[] });
        return next;
      });
      showToast(t('connection_failed'));
    }
  };

  return {
    remoteServers,
    setRemoteServers,
    saveRemoteServers,
    handleAddRemoteServer,
    handleRemoveRemoteServer,
    handleReloadRemoteModels,
  };
};
