import { requestJson } from '../shared/data/http';
import {
  ActiveRouteResult,
  ConnectionRoutingPolicy,
  IpConfigPayload,
  NodeNetworkProfile,
  WifiConnectPayload,
  WifiRadioPayload,
  WifiScanResult,
} from './types';

export async function fetchNodeNetwork(nodeId: string): Promise<NodeNetworkProfile> {
  return requestJson<NodeNetworkProfile>(`/api/v5/nodes/${encodeURIComponent(nodeId)}/network`);
}

export async function updateRoutingPolicy(
  nodeId: string,
  policy: ConnectionRoutingPolicy,
): Promise<{ readonly status: string; readonly policy: ConnectionRoutingPolicy; readonly route: ActiveRouteResult }> {
  return requestJson(`/api/v5/nodes/${encodeURIComponent(nodeId)}/network/policy`, {
    method: 'POST',
    body: JSON.stringify({ policy }),
  });
}

export async function toggleInterface(
  nodeId: string,
  interfaceName: string,
  isUp: boolean,
): Promise<{ readonly success: boolean; readonly route: ActiveRouteResult }> {
  return requestJson(`/api/v5/nodes/${encodeURIComponent(nodeId)}/network/interface/toggle`, {
    method: 'POST',
    body: JSON.stringify({ interface: interfaceName, is_up: isUp }),
  });
}

export async function updateInterfaceIp(
  nodeId: string,
  interfaceName: string,
  config: IpConfigPayload,
): Promise<{ readonly success: boolean; readonly route: ActiveRouteResult }> {
  return requestJson(`/api/v5/nodes/${encodeURIComponent(nodeId)}/network/interface/ip`, {
    method: 'POST',
    body: JSON.stringify({
      interface: interfaceName,
      mode: config.mode,
      ipv4: config.ipv4 ?? null,
      netmask: config.netmask ?? null,
      gateway: config.gateway ?? null,
      dns_primary: config.dns_primary ?? null,
      dns_secondary: config.dns_secondary ?? null,
    }),
  });
}

export async function toggleVpn(
  nodeId: string,
  enabled: boolean,
): Promise<{ readonly success: boolean; readonly vpn_enabled: boolean }> {
  return requestJson(`/api/v5/nodes/${encodeURIComponent(nodeId)}/network/vpn/toggle`, {
    method: 'POST',
    body: JSON.stringify({ enabled }),
  });
}

export async function fetchWifiScan(nodeId: string): Promise<WifiScanResult> {
  return requestJson<WifiScanResult>(`/api/v5/nodes/${encodeURIComponent(nodeId)}/wifi/scan`);
}

export async function connectWifi(
  nodeId: string,
  payload: WifiConnectPayload,
): Promise<{ readonly success: boolean; readonly ssid: string; readonly error?: string }> {
  return requestJson(`/api/v5/nodes/${encodeURIComponent(nodeId)}/wifi/connect`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function disconnectWifi(nodeId: string): Promise<{ readonly success: boolean }> {
  return requestJson(`/api/v5/nodes/${encodeURIComponent(nodeId)}/wifi/disconnect`, {
    method: 'POST',
    body: JSON.stringify({}),
  });
}

export async function toggleWifiRadio(
  nodeId: string,
  payload: WifiRadioPayload,
): Promise<{ readonly success: boolean; readonly radio_enabled: boolean }> {
  return requestJson(`/api/v5/nodes/${encodeURIComponent(nodeId)}/wifi/radio`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
