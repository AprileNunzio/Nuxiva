import { useState } from "react";
import { BatteryMedium, Loader2, Trash2 } from "lucide-react";
import { ConfirmDialog } from "../../../shared/ui/ConfirmDialog";
import { kindIcon } from "../../../shared/bluetooth/kinds";
import { BluetoothDevice, DeviceAction, displayName } from "../../../shared/bluetooth/model";
import { BluetoothHandle, actionKey } from "../../../shared/bluetooth/useBluetooth";

interface FlyoutDeviceProps {
  readonly device: BluetoothDevice;
  readonly handle: BluetoothHandle;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
}

export function FlyoutDevice({ device, handle, t }: FlyoutDeviceProps) {
  const [confirm, setConfirm] = useState(false);
  const Icon = kindIcon(device.kind);
  const name = displayName(device);
  const primary: DeviceAction = device.connected ? "disconnect" : device.paired ? "connect" : "pair";
  const busy = handle.busy === actionKey(primary, device.mac);
  const sub = device.connected ? t("connected") : device.paired ? t("paired") : t(`kind_${device.kind}`);

  return (
    <li className={`bluetooth-device-item${device.connected ? " connected" : ""}`}>
      <div className="bluetooth-device-meta">
        <span className="bluetooth-device-icon">
          <Icon size={18} aria-hidden="true" />
        </span>
        <div className="bluetooth-device-text">
          <span className="bluetooth-device-name">{name}</span>
          <span className="bluetooth-device-sub">
            {sub}
            {device.battery !== null && (
              <span className="bluetooth-device-battery" aria-label={t("battery", { value: device.battery })}>
                <BatteryMedium size={12} aria-hidden="true" />
                {t("battery_value", { value: device.battery })}
              </span>
            )}
          </span>
        </div>
      </div>
      <div className="bluetooth-device-actions">
        <button
          type="button"
          className={`bluetooth-action-btn ${primary}`}
          disabled={handle.busy !== null}
          onClick={() => void handle.act(device, primary)}
        >
          {busy && <Loader2 size={12} className="bluetooth-spinning" aria-hidden="true" />}
          {t(primary)}
        </button>
        {device.paired && (
          <button
            type="button"
            className="bluetooth-action-btn forget"
            disabled={handle.busy !== null}
            title={t("forget")}
            aria-label={t("forget")}
            onClick={() => setConfirm(true)}
          >
            <Trash2 size={14} aria-hidden="true" />
          </button>
        )}
      </div>
      {confirm && (
        <ConfirmDialog
          title={t("forget_title")}
          body={t("forget_body", { name })}
          confirmLabel={t("forget")}
          cancelLabel={t("cancel")}
          pending={handle.busy === actionKey("forget", device.mac)}
          tone="danger"
          onConfirm={() => void handle.act(device, "forget").then(() => setConfirm(false))}
          onCancel={() => setConfirm(false)}
        />
      )}
    </li>
  );
}
