import { getJson, sendJson } from '../shared/http';
import type { BenchmarkResult, DaemonStatus, HardwareProfile, OllamaConfig } from './types';

export async function fetchOllamaStatus(): Promise<DaemonStatus> {
  return getJson<DaemonStatus>('/api/ollama/status');
}

export async function fetchHardwareProfile(): Promise<HardwareProfile> {
  return getJson<HardwareProfile>('/api/ollama/hardware');
}

export async function updateOllamaConfig(config: Partial<OllamaConfig>): Promise<{ status: string; config: OllamaConfig }> {
  return sendJson<{ status: string; config: OllamaConfig }>('/api/ollama/config', 'PUT', config);
}

export async function resetToAutoProfile(): Promise<{ status: string; config: OllamaConfig; hardware: HardwareProfile }> {
  return sendJson<{ status: string; config: OllamaConfig; hardware: HardwareProfile }>('/api/ollama/reset-auto', 'POST');
}

export async function restartOllamaService(): Promise<{ status: string }> {
  return sendJson<{ status: string }>('/api/ollama/restart', 'POST');
}

export async function runOllamaBenchmark(model: string = ''): Promise<BenchmarkResult> {
  return sendJson<BenchmarkResult>('/api/ollama/bench', 'POST', { model });
}
