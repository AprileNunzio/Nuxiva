import { Bluetooth, BluetoothOff, RotateCw, Settings2, X } from "lucide-react";
import { useScopedI18n } from "../../../shared/i18n/useScopedI18n";
import { BluetoothDevice } from "../../../shared/bluetooth/model";
import { FlyoutDevice } from "./FlyoutDevice";
import { useBluetoothState } from "./useBluetoothState";
import { useLocalNodeId } from "./useLocalNodeId";
import type { OpenAppRequest } from "./types";
import "./bluetooth_flyout.css";

interface BluetoothFlyoutProps {
  readonly onClose: () => void;
  readonly onOpenApp?: (request: OpenAppRequest) => void;
}

const bySignal = (a: BluetoothDevice, b: BluetoothDevice) => (b.rssi ?? -999) - (a.rssi ?? -999);

export function BluetoothFlyout({ onClose, onOpenApp }: BluetoothFlyoutProps) {
  const { t } = useScopedI18n("app_shell/tray/bluetooth");
  const { handle, isAvailable, isPowered } = useBluetoothState();
  const localNodeId = useLocalNodeId();
  const devices = handle.state?.devices ?? [];
  const connected = devices.filter((d) => d.connected);
  const paired = devices.filter((d) => d.paired && !d.connected);
  const nearby = devices.filter((d) => !d.paired).sort(bySignal);

  const openApp = () => {
    if (!onOpenApp || !localNodeId) return;
    onOpenApp({ appId: "node_apps/bluetooth", targetNodeId: localNodeId });
    onClose();
  };

  const section = (key: string, list: readonly BluetoothDevice[]) =>
    list.length > 0 && (
      <section className="bluetooth-device-section" aria-label={t(key)}>
        <h3 className="bluetooth-section-title">{t(key)}</h3>
        <ul className="bluetooth-device-list">
          {list.map((d) => (
            <FlyoutDevice key={d.mac} device={d} handle={handle} t={t} />
          ))}
        </ul>
      </section>
    );

  return (
    <div className="bluetooth-flyout" role="dialog" aria-modal="false" aria-labelledby="bluetooth-flyout-title">
      <div className="bluetooth-flyout-header">
        <div className="bluetooth-flyout-title-wrap">
          <span className="bluetooth-flyout-icon">
            <Bluetooth size={18} aria-hidden="true" />
          </span>
          <h2 id="bluetooth-flyout-title" className="bluetooth-flyout-title">
            {t("title")}
          </h2>
        </div>
        <div className="bluetooth-flyout-actions">
          {isAvailable && isPowered && (
            <button
              type="button"
              className="bluetooth-icon-btn"
              onClick={() => void handle.scan()}
              disabled={handle.scanning || handle.busy !== null}
              title={t(handle.scanning ? "scanning" : "scan")}
              aria-label={t(handle.scanning ? "scanning" : "scan")}
            >
              <RotateCw size={15} className={handle.scanning ? "bluetooth-spinning" : ""} aria-hidden="true" />
            </button>
          )}
          <button type="button" className="bluetooth-icon-btn" onClick={onClose} aria-label={t("close")} title={t("close")}>
            <X size={16} aria-hidden="true" />
          </button>
        </div>
      </div>

      <div className="bluetooth-power-bar">
        <span className="bluetooth-power-info">{t(isPowered ? "turn_off" : "turn_on")}</span>
        <button
          type="button"
          role="switch"
          aria-checked={isPowered}
          aria-label={t(isPowered ? "turn_off" : "turn_on")}
          disabled={!isAvailable || handle.busy !== null}
          onClick={() => void handle.power(!isPowered)}
          className={`bluetooth-switch${isPowered ? " on" : ""}`}
        >
          <span className="bluetooth-switch-knob" />
        </button>
      </div>

      <div className="bluetooth-flyout-body" aria-live="polite">
        {handle.state === null ? (
          <div className="bluetooth-empty">
            <span className="bluetooth-empty-hint">{t(handle.reachable ? "loading" : "unreachable")}</span>
          </div>
        ) : !isAvailable ? (
          <div className="bluetooth-empty">
            <BluetoothOff size={32} className="bluetooth-empty-icon" aria-hidden="true" />
            <span className="bluetooth-empty-title">{t(handle.state.enabled ? "no_adapter" : "disabled")}</span>
          </div>
        ) : !isPowered ? (
          <div className="bluetooth-empty">
            <BluetoothOff size={32} className="bluetooth-empty-icon" aria-hidden="true" />
            <span className="bluetooth-empty-title">{t("bluetooth_off")}</span>
            <span className="bluetooth-empty-hint">{t("bluetooth_off_hint")}</span>
          </div>
        ) : (
          <>
            {section("connected_title", connected)}
            {section("my_devices", paired)}
            {section("available", nearby)}
            {devices.length === 0 && (
              <div className="bluetooth-empty">
                <span className="bluetooth-empty-hint">{t(handle.scanning ? "scanning" : "no_devices")}</span>
              </div>
            )}
          </>
        )}
      </div>

      <div className="bluetooth-flyout-footer">
        <button type="button" className="bluetooth-settings-link" disabled={!localNodeId || !onOpenApp} onClick={openApp}>
          <Settings2 size={13} aria-hidden="true" />
          <span>{t("settings")}</span>
        </button>
      </div>
    </div>
  );
}
