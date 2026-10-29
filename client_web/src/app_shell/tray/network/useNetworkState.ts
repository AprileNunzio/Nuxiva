import { useState, useEffect, useCallback } from "react";
import type { NetworkProfile, WifiScanResult } from "./types";

export function useNetworkState() {
  const [profile, setProfile] = useState<NetworkProfile | null>(null);
  const [wifi, setWifi] = useState<WifiScanResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchNetwork = useCallback(async () => {
    try {
      const res = await fetch("/api/v5/nodes/local/network", { credentials: "same-origin" });
      if (!res.ok) throw new Error(String(res.status));
      const data = await res.json();
      setProfile(data);
    } catch {
      setProfile(null);
    }
  }, []);

  const fetchWifi = useCallback(async () => {
    try {
      const res = await fetch("/api/v5/nodes/local/wifi/scan", { credentials: "same-origin" });
      if (!res.ok) throw new Error(String(res.status));
      const data = await res.json();
      setWifi(data);
    } catch {
      setWifi(null);
    }
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    await Promise.all([fetchNetwork(), fetchWifi()]);
    setLoading(false);
  }, [fetchNetwork, fetchWifi]);

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 15000);
    return () => clearInterval(timer);
  }, [refresh]);

  const toggleRadio = useCallback(async (enabled: boolean) => {
    setActionLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/v5/nodes/local/wifi/radio", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Nuxiva-Request": "1" },
        credentials: "same-origin",
        body: JSON.stringify({ action: enabled ? "on" : "off" }),
      });
      if (!res.ok) throw new Error("radio_failed");
      await fetchWifi();
    } catch (e: any) {
      setError(e.message || "error");
    } finally {
      setActionLoading(false);
    }
  }, [fetchWifi]);

  const connectWifi = useCallback(async (ssid: string, psk: string) => {
    setActionLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/v5/nodes/local/wifi/connect", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Nuxiva-Request": "1" },
        credentials: "same-origin",
        body: JSON.stringify({ wifi_ssid: ssid, wifi_key: psk }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.ok === false) {
        throw new Error(data.error || "connect_failed");
      }
      await refresh();
      return true;
    } catch (e: any) {
      setError(e.message || "connect_failed");
      return false;
    } finally {
      setActionLoading(false);
    }
  }, [refresh]);

  const disconnectWifi = useCallback(async () => {
    setActionLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/v5/nodes/local/wifi/disconnect", {
        method: "POST",
        headers: { "X-Nuxiva-Request": "1" },
        credentials: "same-origin",
      });
      if (!res.ok) throw new Error("disconnect_failed");
      await refresh();
    } catch (e: any) {
      setError(e.message || "disconnect_failed");
    } finally {
      setActionLoading(false);
    }
  }, [refresh]);

  const isConnected = !!(
    profile?.active_route?.internet_reachable ||
    profile?.interfaces?.some((i) => i.ipv4 && i.is_up)
  );

  const isWifiActive = !!(
    wifi?.current_ssid ||
    profile?.interfaces?.some((i) => i.kind === "wifi" && i.is_up)
  );

  return {
    profile,
    wifi,
    loading,
    actionLoading,
    error,
    refresh,
    toggleRadio,
    connectWifi,
    disconnectWifi,
    isConnected,
    isWifiActive,
  };
}
