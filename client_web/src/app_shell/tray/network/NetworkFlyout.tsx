import { useState, useMemo } from "react";
import {
  Wifi,
  WifiOff,
  Network,
  RotateCw,
  X,
  Lock,
  ExternalLink,
  Globe,
} from "lucide-react";
import { useNetworkState } from "./useNetworkState";
import { MD3Switch } from "../../../shared/components/MD3Switch";
import it from "./language/it.json";
import en from "./language/en.json";
import es from "./language/es.json";
import fr from "./language/fr.json";
import "./network_flyout.css";

const dicts: Record<string, Record<string, string>> = { it, en, es, fr };

interface NetworkFlyoutProps {
  onClose: () => void;
  onOpenApp?: (appId: any) => void;
  lang?: string;
}

export function NetworkFlyout({ onClose, onOpenApp, lang = "it" }: NetworkFlyoutProps) {
  const t = useMemo(() => {
    const d = dicts[lang] || dicts.it;
    return (key: string) => d[key] || key;
  }, [lang]);

  const {
    profile,
    wifi,
    loading,
    actionLoading,
    refresh,
    toggleRadio,
    connectWifi,
    disconnectWifi,
    isConnected,
  } = useNetworkState();

  const [activeTab, setActiveTab] = useState<"wifi" | "interfaces">("wifi");
  const [selectedSsid, setSelectedSsid] = useState<string | null>(null);
  const [password, setPassword] = useState("");

  const handleConnect = async (ssid: string) => {
    await connectWifi(ssid, password);
    setSelectedSsid(null);
    setPassword("");
  };

  return (
    <div className="network-flyout" role="dialog" aria-modal="false" aria-labelledby="network-flyout-title">
      <div className="network-flyout-header">
        <span id="network-flyout-title" className="network-flyout-title">
          {t("title")}
        </span>
        <div className="network-flyout-actions">
          <button
            className="network-icon-btn"
            title={t("refresh")}
            aria-label={t("refresh")}
            onClick={() => refresh()}
            disabled={loading}
          >
            <RotateCw size={14} className={loading ? "network-spinning" : ""} />
          </button>
          <button
            className="network-icon-btn"
            title={t("close")}
            aria-label={t("close")}
            onClick={onClose}
          >
            <X size={15} />
          </button>
        </div>
      </div>

      <div className="network-flyout-tabs">
        <button
          className={`network-tab-btn ${activeTab === "wifi" ? "active" : ""}`}
          onClick={() => setActiveTab("wifi")}
        >
          <Wifi size={13} />
          {t("wifi")}
        </button>
        <button
          className={`network-tab-btn ${activeTab === "interfaces" ? "active" : ""}`}
          onClick={() => setActiveTab("interfaces")}
        >
          <Network size={13} />
          {t("interfaces")}
        </button>
      </div>

      <div className="network-flyout-body">
        {activeTab === "wifi" ? (
          <>
            <div className="network-radio-row">
              <span className="network-radio-label">
                {wifi?.radio_enabled ? t("wifi_enabled") : t("wifi_disabled")}
              </span>
              <MD3Switch
                checked={wifi?.radio_enabled ?? true}
                disabled={actionLoading}
                onChange={toggleRadio}
                ariaLabel={wifi?.radio_enabled ? t("wifi_enabled") : t("wifi_disabled")}
              />
            </div>

            {wifi?.radio_enabled === false ? (
              <div className="network-empty">
                <WifiOff size={28} />
                <span>{t("wifi_disabled")}</span>
              </div>
            ) : !wifi?.networks || wifi.networks.length === 0 ? (
              <div className="network-empty">
                <span>{loading ? t("scanning") : t("no_networks")}</span>
              </div>
            ) : (
              <div className="network-list">
                {wifi.networks.map((net) => {
                  const isCur = net.is_connected || net.ssid === wifi.current_ssid;
                  const isExpanded = selectedSsid === net.ssid;
                  return (
                    <div
                      key={net.ssid}
                      className={`network-item ${isCur ? "connected" : ""}`}
                    >
                      <div className="network-item-row">
                        <div className="network-item-left">
                          <Wifi size={14} className={isCur ? "network-icon-online" : "network-icon-muted"} />
                          <span className="network-item-ssid">{net.ssid}</span>
                          {net.security && !isCur && <Lock size={11} className="network-icon-muted" />}
                          {isCur && (
                            <span className="network-item-badge">
                              {t("connected")}
                            </span>
                          )}
                        </div>
                        {isCur ? (
                          <button
                            className="network-item-btn danger"
                            disabled={actionLoading}
                            onClick={() => disconnectWifi()}
                          >
                            {t("disconnect")}
                          </button>
                        ) : (
                          <button
                            className="network-item-btn primary"
                            disabled={actionLoading}
                            onClick={() => {
                              if (isExpanded) {
                                setSelectedSsid(null);
                              } else if (!net.security) {
                                connectWifi(net.ssid, "");
                              } else {
                                setSelectedSsid(net.ssid);
                                setPassword("");
                              }
                            }}
                          >
                            {isExpanded ? t("cancel") : t("connect")}
                          </button>
                        )}
                      </div>

                      {isExpanded && !isCur && (
                        <div className="network-connect-form">
                          <input
                            type="password"
                            className="network-password-input"
                            placeholder={t("enter_password")}
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter" && password) {
                                handleConnect(net.ssid);
                              }
                            }}
                            autoFocus
                          />
                          <button
                            className="network-item-btn primary"
                            disabled={actionLoading || !password}
                            onClick={() => handleConnect(net.ssid)}
                          >
                            {t("connect")}
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </>
        ) : (
          <div className="network-list">
            {profile?.interfaces && profile.interfaces.length > 0 ? (
              profile.interfaces.map((iface) => (
                <div key={iface.name} className="iface-card">
                  <div className="iface-card-header">
                    <span className="iface-name">{iface.name}</span>
                    <span className={`iface-status ${iface.is_up ? "up" : "down"}`}>
                      {iface.is_up ? "UP" : "DOWN"}
                    </span>
                  </div>
                  {iface.ipv4 && (
                    <div className="iface-detail">
                      <span>{t("ip_address")}</span>
                      <span className="iface-val">{iface.ipv4}</span>
                    </div>
                  )}
                  {iface.mac_address && (
                    <div className="iface-detail">
                      <span>{t("mac_address")}</span>
                      <span className="iface-val">{iface.mac_address}</span>
                    </div>
                  )}
                  {iface.gateway && (
                    <div className="iface-detail">
                      <span>{t("gateway")}</span>
                      <span className="iface-val">{iface.gateway}</span>
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div className="network-empty">
                <Globe size={24} />
                <span>{t("no_networks")}</span>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="network-flyout-footer">
        <span className="network-status-label">
          {isConnected ? t("connected") : t("disconnected")}
        </span>
        {onOpenApp && (
          <button
            className="network-settings-link"
            onClick={() => {
              const targetNode = profile?.node_id || "virtual_core";
              onOpenApp({
                appId: "node_apps/console",
                targetNodeId: targetNode,
                initialPayload: { name: targetNode, module: "connections" },
              });
              onClose();
            }}
          >
            <span>{t("manage_network")}</span>
            <ExternalLink size={12} />
          </button>
        )}
      </div>
    </div>
  );
}
