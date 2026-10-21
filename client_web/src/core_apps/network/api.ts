/**
 * Network Application API & MCP Client
 * Communicates with /api/network REST endpoints and Nuxiva MCP tool services.
 */

export interface DiscoveredService {
  readonly port: number;
  readonly service: string;
}

export interface NetworkDevice {
  readonly key: string;
  readonly ip: string;
  readonly mac?: string;
  readonly vendor?: string;
  readonly type?: string;
  readonly os?: string;
  readonly name?: string;
  readonly room?: string;
  readonly trusted?: boolean;
  readonly online?: boolean;
  readonly ports?: readonly DiscoveredService[];
  readonly firewall?: unknown;
}

export interface NetworkDiscoveryResponse {
  readonly devices: readonly NetworkDevice[];
  readonly active_subnets?: readonly string[];
  readonly last_scan?: string;
  readonly scanning?: boolean;
}

export interface DeviceUpdatePayload {
  readonly name?: string;
  readonly room?: string;
  readonly type?: string;
  readonly trusted?: boolean;
}

export interface MCPToolResult {
  readonly content?: ReadonlyArray<{ readonly type: string; readonly text?: string }>;
  readonly isError?: boolean;
}

const HEADERS = {
  Accept: 'application/json',
  'Content-Type': 'application/json',
  'X-Nuxiva-Request': '1',
};

/**
 * Fetch all discovered network devices from the backend.
 */
export async function fetchNetworkDevices(signal?: AbortSignal): Promise<NetworkDiscoveryResponse> {
  const response = await fetch('/api/network', {
    headers: { Accept: 'application/json', 'X-Nuxiva-Request': '1' },
    cache: 'no-store',
    signal,
  });
  if (!response.ok) {
    throw new Error(`network_api_http_${response.status}`);
  }
  return response.json();
}

/**
 * Trigger an active ARP/mDNS/LLMNR network scan across local subnets.
 */
export async function triggerNetworkScan(): Promise<{ readonly ok: boolean }> {
  const response = await fetch('/api/network/scan', {
    method: 'POST',
    headers: HEADERS,
    cache: 'no-store',
  });
  if (!response.ok) {
    throw new Error(`network_scan_http_${response.status}`);
  }
  return response.json();
}

/**
 * Trigger a deep scan (port analysis and fingerprinting) for a specific device.
 */
export async function studyDevice(key: string): Promise<{ readonly ok: boolean }> {
  const response = await fetch(`/api/network/study/${encodeURIComponent(key)}`, {
    method: 'POST',
    headers: HEADERS,
    cache: 'no-store',
  });
  if (!response.ok) {
    throw new Error(`network_study_http_${response.status}`);
  }
  return response.json();
}

/**
 * Update device metadata (custom name, room, type, trusted status).
 */
export async function updateDevice(key: string, payload: DeviceUpdatePayload): Promise<{ readonly ok: boolean }> {
  const response = await fetch(`/api/network/devices/${encodeURIComponent(key)}`, {
    method: 'PUT',
    headers: HEADERS,
    body: JSON.stringify(payload),
    cache: 'no-store',
  });
  if (!response.ok) {
    throw new Error(`network_update_http_${response.status}`);
  }
  return response.json();
}

/**
 * Query the who_is MCP tool to ask the network assistant for semantic context
 * on an IP or MAC address.
 */
export async function queryWhoIsMCP(address: string): Promise<string> {
  try {
    const response = await fetch('/mcp', {
      method: 'POST',
      headers: HEADERS,
      body: JSON.stringify({
        jsonrpc: '2.0',
        id: `mcp-${Date.now()}`,
        method: 'tools/call',
        params: {
          name: 'who_is',
          arguments: { address },
        },
      }),
      cache: 'no-store',
    });
    if (!response.ok) {
      return '';
    }
    const data: { result?: MCPToolResult } = await response.json();
    const textItem = data.result?.content?.find((c) => c.type === 'text' && c.text);
    return textItem?.text ?? '';
  } catch {
    return '';
  }
}
