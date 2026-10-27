import { useMemo } from "react";
import {
  Bluetooth,
  BluetoothOff,
  RotateCw,
  X,
  Headphones,
  Speaker,
  Smartphone,
  Radio,
  Trash2,
  ExternalLink,
} from "lucide-react";
import { useBluetoothState } from "./useBluetoothState";
import it from "./language/it.json";
import en from "./language/en.json";
import es from "./language/es.json";
import fr from "./language/fr.json";
import "./bluetooth_flyout.css";

const dicts: Record<string, Record<string, string>> = { it, en, es, fr };

interface BluetoothFlyoutProps {
  onClose: () => void;
  onOpenApp?: (appId: string) => void;
  lang?: string;
}

export function BluetoothFlyout({ onClose, onOpenApp, lang = "it" }: BluetoothFlyoutProps) {
  const t = useMemo(() => {
    const d = dicts[lang] || dicts.it;
    return (key: string) => d[key] || key;
  }, [lang]);

  const {
    controller,
    devices,
    loading,
    scanning,
    actionLoading,
    isAvailable,
    isPowered,
    togglePower,
    startScan,
    connectDevice,
    disconnectDevice,
    pairDevice,
    forgetDevice,
  } = useBluetoothState();

  const getDeviceIcon = (device: { name: string; icon?: string }) => {
    const n = (device.name || "").toLowerCase();
    const icon = (device.icon || "").toLowerCase();
    if (icon.includes("headphone") || n.includes("cuffi") || n.includes("headphone") || n.includes("airpod")) {
      return <Headphones size={18} />;
    }
    if (icon.includes("audio") || icon.includes("speaker") || n.includes("cassa") || n.includes("speaker")) {
      return <Speaker size={18} />;
    }
    if (icon.includes("phone") || n.includes("phone") || n.includes("iphone") || n.includes("galaxy")) {
      return <Smartphone size={18} />;
    }
    return <Radio size={18} />;
  };

  const connectedDevices = devices.filter((d) => d.connected);
  const otherDevices = devices.filter((d) => !d.connected);

  return (
    <div className="bluetooth-flyout" role="dialog" aria-modal="true">
      <div className="bluetooth-flyout-header">
        <div className="bluetooth-flyout-title-wrap">
          <span className="bluetooth-flyout-icon">
            <Bluetooth size={18} />
          </span>
          <span className="bluetooth-flyout-title">{t("title")}</span>
        </div>
        <div className="bluetooth-flyout-actions">
          {isPowered && (
            <button
              className="bluetooth-icon-btn"
              onClick={startScan}
              disabled={scanning || actionLoading}
              title={scanning ? t("scanning") : t("scan")}
              aria-label={scanning ? t("scanning") : t("scan")}
            >
              <RotateCw size={15} className={scanning || loading ? "bluetooth-spinning" : ""} />
            </button>
          )}
          <button className="bluetooth-icon-btn" onClick={onClose} aria-label={t("close")} title={t("close")}>
            <X size={16} />
          </button>
        </div>
      </div>

      <div className="bluetooth-power-bar">
        <span className="bluetooth-power-info">{isPowered ? t("turn_off") : t("turn_on")}</span>
        <label className="bluetooth-toggle-switch">
          <input
            type="checkbox"
            checked={isPowered}
            disabled={!isAvailable || actionLoading}
            onChange={(e) => togglePower(e.target.checked)}
          />
          <span className="bluetooth-toggle-slider" />
        </label>
      </div>

      <div className="bluetooth-flyout-body">
        {!isAvailable ? (
          <div className="bluetooth-empty">
            <BluetoothOff size={32} className="bluetooth-empty-icon" />
            <span className="bluetooth-empty-title">{t("no_adapter")}</span>
          </div>
        ) : !isPowered ? (
          <div className="bluetooth-empty">
            <BluetoothOff size={32} className="bluetooth-empty-icon" />
            <span className="bluetooth-empty-title">{t("bluetooth_off")}</span>
            <span className="bluetooth-empty-hint">{t("bluetooth_off_hint")}</span>
          </div>
        ) : (
          <>
            {connectedDevices.length > 0 && (
              <div className="bluetooth-device-section">
                <div className="bluetooth-section-title">{t("connected")}</div>
                <div className="bluetooth-device-list">
                  {connectedDevices.map((d) => (
                    <div key={d.mac} className="bluetooth-device-item connected">
                      <div className="bluetooth-device-meta">
                        <span className="bluetooth-device-icon">{getDeviceIcon(d)}</span>
                        <div className="bluetooth-device-text">
                          <span className="bluetooth-device-name">{d.name || d.mac}</span>
                          <span className="bluetooth-device-sub">{t("connected")}</span>
                        </div>
                      </div>
                      <div className="bluetooth-device-actions">
                        <button
                          className="bluetooth-action-btn disconnect"
                          disabled={actionLoading}
                          onClick={() => disconnectDevice(d.mac)}
                        >
                          {t("disconnect")}
                        </button>
                        <button
                          className="bluetooth-action-btn forget"
                          disabled={actionLoading}
                          title={t("forget")}
                          onClick={() => forgetDevice(d.mac)}
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="bluetooth-device-section">
              <div className="bluetooth-section-title">
                {connectedDevices.length > 0 ? t("available") : t("my_devices")}
              </div>
              <div className="bluetooth-device-list">
                {otherDevices.length === 0 ? (
                  <div className="bluetooth-empty">
                    <span className="bluetooth-empty-hint">
                      {scanning ? t("scanning") : t("no_devices")}
                    </span>
                  </div>
                ) : (
                  otherDevices.map((d) => (
                    <div key={d.mac} className="bluetooth-device-item">
                      <div className="bluetooth-device-meta">
                        <span className="bluetooth-device-icon">{getDeviceIcon(d)}</span>
                        <div className="bluetooth-device-text">
                          <span className="bluetooth-device-name">{d.name || d.mac}</span>
                          <span className="bluetooth-device-sub">
                            {d.paired ? t("paired") : d.mac}
                          </span>
                        </div>
                      </div>
                      <div className="bluetooth-device-actions">
                        <button
                          className="bluetooth-action-btn connect"
                          disabled={actionLoading}
                          onClick={() => (d.paired ? connectDevice(d.mac) : pairDevice(d.mac))}
                        >
                          {d.paired ? t("connect") : t("pair")}
                        </button>
                        {d.paired && (
                          <button
                            className="bluetooth-action-btn forget"
                            disabled={actionLoading}
                            title={t("forget")}
                            onClick={() => forgetDevice(d.mac)}
                          >
                            <Trash2 size={14} />
                          </button>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </>
        )}
      </div>

      <div className="bluetooth-flyout-footer">
        <button
          className="bluetooth-settings-link"
          onClick={() => {
            if (onOpenApp) onOpenApp("features_hub");
            onClose();
          }}
        >
          <ExternalLink size={13} />
          <span>{t("settings")}</span>
        </button>
      </div>
    </div>
  );
}
