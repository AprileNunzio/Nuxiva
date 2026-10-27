import { useState, useEffect, useCallback } from "react";
import type { BluetoothController, BluetoothDevice, BluetoothPayload } from "./types";

export function useBluetoothState() {
  const [controller, setController] = useState<BluetoothController | null>(null);
  const [devices, setDevices] = useState<BluetoothDevice[]>([]);
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchBluetooth = useCallback(async () => {
    try {
      const res = await fetch("/api/bluetooth");
      if (!res.ok) throw new Error(String(res.status));
      const data: BluetoothPayload = await res.json();
      setController(data.controller || null);
      setDevices(Array.isArray(data.devices) ? data.devices : []);
      if (typeof data.scanning === "boolean") {
        setScanning(data.scanning);
      } else if (data.controller?.discovering) {
        setScanning(true);
      }
    } catch {
      setController(null);
      setDevices([]);
    }
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    await fetchBluetooth();
    setLoading(false);
  }, [fetchBluetooth]);

  useEffect(() => {
    refresh();
    const timer = setInterval(fetchBluetooth, 10000);
    return () => clearInterval(timer);
  }, [refresh, fetchBluetooth]);

  const togglePower = useCallback(async (on: boolean) => {
    setActionLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/bluetooth/power", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ on }),
      });
      if (!res.ok) throw new Error("power_failed");
      const data: BluetoothPayload = await res.json();
      setController(data.controller || null);
      setDevices(Array.isArray(data.devices) ? data.devices : []);
    } catch (e: any) {
      setError(e.message || "error");
    } finally {
      setActionLoading(false);
    }
  }, []);

  const startScan = useCallback(async () => {
    setActionLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/bluetooth/scan", { method: "POST" });
      if (!res.ok) throw new Error("scan_failed");
      setScanning(true);
      setTimeout(() => {
        fetchBluetooth();
        setScanning(false);
      }, 5000);
    } catch (e: any) {
      setError(e.message || "error");
    } finally {
      setActionLoading(false);
    }
  }, [fetchBluetooth]);

  const connectDevice = useCallback(async (mac: string) => {
    setActionLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/bluetooth/devices/${encodeURIComponent(mac)}/connect`, { method: "POST" });
      if (!res.ok) throw new Error("connect_failed");
      const data: BluetoothPayload = await res.json();
      setController(data.controller || null);
      setDevices(Array.isArray(data.devices) ? data.devices : []);
      return true;
    } catch (e: any) {
      setError(e.message || "error");
      return false;
    } finally {
      setActionLoading(false);
    }
  }, []);

  const disconnectDevice = useCallback(async (mac: string) => {
    setActionLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/bluetooth/devices/${encodeURIComponent(mac)}/disconnect`, { method: "POST" });
      if (!res.ok) throw new Error("disconnect_failed");
      const data: BluetoothPayload = await res.json();
      setController(data.controller || null);
      setDevices(Array.isArray(data.devices) ? data.devices : []);
      return true;
    } catch (e: any) {
      setError(e.message || "error");
      return false;
    } finally {
      setActionLoading(false);
    }
  }, []);

  const pairDevice = useCallback(async (mac: string) => {
    setActionLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/bluetooth/devices/${encodeURIComponent(mac)}/pair`, { method: "POST" });
      if (!res.ok) throw new Error("pair_failed");
      const data: BluetoothPayload = await res.json();
      setController(data.controller || null);
      setDevices(Array.isArray(data.devices) ? data.devices : []);
      return true;
    } catch (e: any) {
      setError(e.message || "error");
      return false;
    } finally {
      setActionLoading(false);
    }
  }, []);

  const forgetDevice = useCallback(async (mac: string) => {
    setActionLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/bluetooth/devices/${encodeURIComponent(mac)}/forget`, { method: "POST" });
      if (!res.ok) throw new Error("forget_failed");
      const data: BluetoothPayload = await res.json();
      setController(data.controller || null);
      setDevices(Array.isArray(data.devices) ? data.devices : []);
      return true;
    } catch (e: any) {
      setError(e.message || "error");
      return false;
    } finally {
      setActionLoading(false);
    }
  }, []);

  const isAvailable = Boolean(controller?.present || controller?.installed);
  const isPowered = Boolean(controller?.powered);

  return {
    controller,
    devices,
    loading,
    scanning,
    actionLoading,
    error,
    isAvailable,
    isPowered,
    refresh,
    togglePower,
    startScan,
    connectDevice,
    disconnectDevice,
    pairDevice,
    forgetDevice,
  };
}
