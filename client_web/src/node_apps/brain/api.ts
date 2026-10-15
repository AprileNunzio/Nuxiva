import { RemoteOllamaInstance, TestResult } from './types';

export async function fetchBrainData(nodeId: string) {
  const res = await fetch(`/api/v5/nodes/${nodeId}/brain`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function saveBrainConfig(nodeId: string, config: any) {
  const res = await fetch(`/api/v5/nodes/${nodeId}/brain`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function installLocalOllama(nodeId: string) {
  const res = await fetch(`/api/v5/nodes/${nodeId}/brain/ollama/install`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ node_id: nodeId }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function uninstallLocalOllama(nodeId: string) {
  const res = await fetch(`/api/v5/nodes/${nodeId}/brain/ollama/uninstall`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ node_id: nodeId }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function testRemoteMeshInstance(nodeId: string, host_url: string, model?: string) {
  const res = await fetch(`/api/v5/nodes/${nodeId}/brain/remote_mesh/test`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ host_url, model }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function saveRemoteMeshInstances(nodeId: string, instances: RemoteOllamaInstance[]) {
  const res = await fetch(`/api/v5/nodes/${nodeId}/brain/remote_mesh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ instances }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function testBrainInference(nodeId: string, payload: any): Promise<TestResult> {
  const res = await fetch(`/api/v5/nodes/${nodeId}/brain/test`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function pullBrainModel(nodeId: string, model: string, host?: string) {
  const res = await fetch(`/api/v5/nodes/${nodeId}/brain/pull`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model, host }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
