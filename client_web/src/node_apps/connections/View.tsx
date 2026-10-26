import React, { useCallback, useEffect, useState } from 'react';
import { AlertCircle, Cpu, Loader2, Network, RefreshCw, Shield, Wifi } from 'lucide-react';
import { ControlScope } from '../console/data/nodeConsoleApi';
import { ModuleFrame } from '../shared/components/ModuleFrame';
import {
  connectWifi,
  disconnectWifi,
  fetchNodeNetwork,
  fetchWifiScan,
  toggleInterface,
  toggleVpn,
  toggleWifiRadio,
  updateInterfaceIp,
  updateRoutingPolicy,
} from './api';
import { GsmModemCard } from './components/GsmModemCard';
import { InterfaceCard } from './components/InterfaceCard';
import { IpConfigModal } from './components/IpConfigModal';
import { PolicySelector } from './components/PolicySelector';
import { RouteStatusBanner } from './components/RouteStatusBanner';
import { VpnTunnelCard } from './components/VpnTunnelCard';
import { WifiScanner } from './components/WifiScanner';
import { useConnectionsI18n } from './scope';
import {
  ConnectionRoutingPolicy,
  IpConfigPayload,
  NetworkInterface,
  NodeNetworkProfile,
  WifiConnectPayload,
  WifiScanResult,
} from './types';

interface ConnectionsViewProps {
  readonly nodeId?: string;
  readonly scope?: ControlScope;
  readonly initialPayload?: Record<string, unknown>;
}

type ConnectionsTab = 'overview' | 'interfaces' | 'wifi' | 'vpn_cellular';

export const View: React.FC<ConnectionsViewProps> = ({ nodeId = '', scope = 'mesh', initialPayload }) => {
  const { t } = useConnectionsI18n();
  const targetId = nodeId || (typeof initialPayload?.nodeId === 'string' ? initialPayload.nodeId : 'virtual_core');
  const [profile, setProfile] = useState<NodeNetworkProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<ConnectionsTab>('overview');
  const [updatingPolicy, setUpdatingPolicy] = useState(false);
  const [togglingVpn, setTogglingVpn] = useState(false);
  const [savingIp, setSavingIp] = useState(false);
  const [editingIface, setEditingIface] = useState<NetworkInterface | null>(null);

  const [wifiScan, setWifiScan] = useState<WifiScanResult | null>(null);
  const [wifiScanning, setWifiScanning] = useState(false);
  const [wifiConnecting, setWifiConnecting] = useState(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchNodeNetwork(targetId);
      setProfile(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'error_loading_network');
    } finally {
      setLoading(false);
    }
  }, [targetId]);

  const loadWifi = useCallback(async () => {
    try {
      setWifiScanning(true);
      const data = await fetchWifiScan(targetId);
      setWifiScan(data);
    } catch {
      setWifiScan(null);
    } finally {
      setWifiScanning(false);
    }
  }, [targetId]);

  useEffect(() => {
    void loadData();
    void loadWifi();
  }, [loadData, loadWifi]);

  const handleSelectPolicy = async (policy: ConnectionRoutingPolicy) => {
    if (!profile || updatingPolicy) return;
    try {
      setUpdatingPolicy(true);
      const res = await updateRoutingPolicy(targetId, policy);
      setProfile((prev) =>
        prev
          ? {
              ...prev,
              policy: res.policy,
              active_route: res.route,
            }
          : null,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'error_updating_policy');
    } finally {
      setUpdatingPolicy(false);
    }
  };

  const handleToggleInterface = async (name: string, nextUp: boolean) => {
    if (!profile) return;
    try {
      const res = await toggleInterface(targetId, name, nextUp);
      setProfile((prev) => {
        if (!prev) return null;
        const updatedInterfaces = prev.interfaces.map((i) => (i.name === name ? { ...i, is_up: nextUp } : i));
        return {
          ...prev,
          interfaces: updatedInterfaces,
          active_route: res.route,
        };
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'error_toggling_interface');
    }
  };

  const handleSaveIpConfig = async (config: IpConfigPayload) => {
    if (!profile || !editingIface || savingIp) return;
    try {
      setSavingIp(true);
      const res = await updateInterfaceIp(targetId, editingIface.name, config);
      setProfile((prev) => {
        if (!prev) return null;
        const updatedInterfaces = prev.interfaces.map((i) =>
          i.name === editingIface.name
            ? {
                ...i,
                ip_mode: config.mode,
                ipv4: config.ipv4 ?? null,
                netmask: config.netmask ?? null,
                gateway: config.gateway ?? null,
                dns_primary: config.dns_primary ?? null,
                dns_secondary: config.dns_secondary ?? null,
              }
            : i,
        );
        return {
          ...prev,
          interfaces: updatedInterfaces,
          active_route: res.route,
        };
      });
      setEditingIface(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'error_saving_ip');
    } finally {
      setSavingIp(false);
    }
  };

  const handleToggleVpn = async (enabled: boolean) => {
    if (!profile || togglingVpn) return;
    try {
      setTogglingVpn(true);
      const res = await toggleVpn(targetId, enabled);
      setProfile((prev) =>
        prev
          ? {
              ...prev,
              vpn: {
                ...prev.vpn,
                enabled: res.vpn_enabled,
              },
            }
          : null,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'error_toggling_vpn');
    } finally {
      setTogglingVpn(false);
    }
  };

  const handleConnectWifi = async (payload: WifiConnectPayload) => {
    try {
      setWifiConnecting(true);
      setError(null);
      const res = await connectWifi(targetId, payload);
      if (!res.success && res.error) {
        setError(res.error);
      }
      await loadWifi();
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'error_connecting_wifi');
    } finally {
      setWifiConnecting(false);
    }
  };

  const handleDisconnectWifi = async () => {
    try {
      setWifiConnecting(true);
      await disconnectWifi(targetId);
      await loadWifi();
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'error_disconnecting_wifi');
    } finally {
      setWifiConnecting(false);
    }
  };

  const handleToggleWifiRadio = async (enabled: boolean) => {
    try {
      await toggleWifiRadio(targetId, { enabled, interface: wifiScan?.interface });
      await loadWifi();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'error_toggling_wifi_radio');
    }
  };

  const tabs: readonly { id: ConnectionsTab; labelKey: string; icon: React.FC<{ className?: string }> }[] = [
    { id: 'overview', labelKey: 'tab_overview', icon: Network },
    { id: 'interfaces', labelKey: 'tab_interfaces', icon: Cpu },
    { id: 'wifi', labelKey: 'tab_wifi', icon: Wifi },
    { id: 'vpn_cellular', labelKey: 'tab_vpn_cellular', icon: Shield },
  ];

  return (
    <ModuleFrame
      icon={Network}
      title={t('title')}
      subtitle={t('description')}
      badge={targetId ? `${targetId} (${t(`scope_${scope}`)})` : t(`scope_${scope}`)}
    >
      <div className="flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-1.5 overflow-x-auto rounded-2xl border border-slate-800/80 bg-slate-900/60 p-1 backdrop-blur-md">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 rounded-xl px-3 py-1.5 text-xs font-semibold transition ${
                    isActive
                      ? 'border border-cyan-400/50 bg-gradient-to-r from-cyan-500/20 to-blue-500/20 text-cyan-200 shadow-xs'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                  }`}
                >
                  <Icon className={`h-3.5 w-3.5 ${isActive ? 'text-cyan-300' : 'text-slate-500'}`} />
                  {t(tab.labelKey)}
                </button>
              );
            })}
          </div>

          <div className="flex items-center gap-2 self-end sm:self-center">
            <span className="font-mono text-xs text-slate-400">
              {t('target_node')}: <strong className="text-cyan-300">{targetId}</strong>
            </span>
            <button
              type="button"
              onClick={() => {
                void loadData();
                void loadWifi();
              }}
              disabled={loading || wifiScanning}
              className="flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900/80 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:border-slate-700 hover:text-white transition disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading || wifiScanning ? 'animate-spin text-cyan-300' : ''}`} />
              {t('refresh')}
            </button>
          </div>
        </div>

        {error && (
          <div className="flex items-center gap-2 rounded-xl border border-rose-500/40 bg-rose-500/10 p-3 text-xs text-rose-300">
            <AlertCircle className="h-4 w-4 shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
        )}

        {loading && !profile && (
          <div className="flex flex-col items-center justify-center p-12 text-slate-400 gap-3">
            <Loader2 className="h-8 w-8 animate-spin text-cyan-400" />
            <span className="text-xs">{t('loading_network_config')}...</span>
          </div>
        )}

        {profile && (
          <>
            {activeTab === 'overview' && (
              <div className="flex flex-col gap-4">
                <RouteStatusBanner route={profile.active_route} policy={profile.policy} t={t} />

                <PolicySelector
                  currentPolicy={profile.policy}
                  updating={updatingPolicy}
                  onSelectPolicy={handleSelectPolicy}
                  t={t}
                />

                <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
                      {t('interfaces_title')} ({profile.interfaces.length})
                    </h3>
                    <button
                      type="button"
                      onClick={() => setActiveTab('interfaces')}
                      className="text-xs font-semibold text-cyan-400 hover:text-cyan-300"
                    >
                      {t('view_all_interfaces')} →
                    </button>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    {profile.interfaces.slice(0, 3).map((iface) => (
                      <div
                        key={iface.name}
                        className="rounded-xl border border-slate-800 bg-slate-950/70 p-3 flex flex-col justify-between gap-2"
                      >
                        <div className="flex items-center justify-between">
                          <strong className="font-mono text-xs text-white truncate">{iface.name}</strong>
                          <span
                            className={`h-2 w-2 rounded-full ${
                              iface.is_up ? 'bg-emerald-400 shadow-xs shadow-emerald-400' : 'bg-slate-600'
                            }`}
                          />
                        </div>
                        <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
                          <span>{iface.ipv4 || '—'}</span>
                          <span>{iface.speed_mbps ? `${iface.speed_mbps} Mbps` : '—'}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'interfaces' && (
              <div className="flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
                    {t('interfaces_title')} ({profile.interfaces.length})
                  </h3>
                </div>

                <div className="grid gap-4 lg:grid-cols-2">
                  {profile.interfaces.map((iface) => (
                    <InterfaceCard
                      key={iface.name}
                      iface={iface}
                      isPrimary={profile.active_route.primary_interface === iface.name}
                      isSecondary={profile.active_route.secondary_interface === iface.name}
                      onToggle={handleToggleInterface}
                      onEditIp={(selected) => setEditingIface(selected)}
                      t={t}
                    />
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'wifi' && (
              <WifiScanner
                scanResult={wifiScan}
                scanning={wifiScanning}
                connecting={wifiConnecting}
                onRescan={() => void loadWifi()}
                onConnect={handleConnectWifi}
                onDisconnect={handleDisconnectWifi}
                onToggleRadio={handleToggleWifiRadio}
                t={t}
              />
            )}

            {activeTab === 'vpn_cellular' && (
              <div className="grid gap-4 lg:grid-cols-2">
                <VpnTunnelCard
                  vpn={profile.vpn}
                  toggling={togglingVpn}
                  onToggleVpn={handleToggleVpn}
                  t={t}
                />
                <GsmModemCard modem={profile.gsm_modem} t={t} />
              </div>
            )}

            {editingIface && (
              <IpConfigModal
                iface={editingIface}
                isOpen={Boolean(editingIface)}
                saving={savingIp}
                onClose={() => setEditingIface(null)}
                onSave={handleSaveIpConfig}
                t={t}
              />
            )}
          </>
        )}
      </div>
    </ModuleFrame>
  );
};

export default View;