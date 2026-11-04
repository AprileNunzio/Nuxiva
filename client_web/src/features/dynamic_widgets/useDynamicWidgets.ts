import { adminPath } from '../../shared/http/basePath';
import { useState, useEffect, useCallback, useRef } from "react";
import { WidgetItem, WidgetActionPayload } from "./types";

export function useDynamicWidgets() {
  const [widgets, setWidgets] = useState<WidgetItem[]>([]);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const fetchWidgets = useCallback(async () => {
    try {
      setIsLoading(true);
      const res = await fetch("/api/v2/widgets");
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const data: WidgetItem[] = await res.json();
      setWidgets(data);
      setError(null);
    } catch (err: any) {
      setError(err?.message || "Failed to load widgets");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const executeAction = useCallback(async (widgetId: string, action: string, payload: Record<string, any> = {}) => {
    try {
      const res = await fetch(`/api/v2/widgets/${encodeURIComponent(widgetId)}/action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, payload }),
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const outcome = await res.json();
      setWidgets((prev) =>
        prev.map((w) => {
          if (w.id === widgetId && outcome.result) {
            return { ...w, state: { ...w.state, ...outcome.result } };
          }
          return w;
        })
      );
      return outcome;
    } catch (err: any) {
      setError(err?.message || "Action failed");
      throw err;
    }
  }, []);

  useEffect(() => {
    fetchWidgets();

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}${adminPath("/api/v2/widgets/ws")}`;

    let active = true;
    let socket: WebSocket | null = null;
    let timer: any = null;

    function connect() {
      if (!active) return;
      socket = new WebSocket(wsUrl);
      wsRef.current = socket;

      socket.onopen = () => {
        if (!active) return;
        setIsConnected(true);
      };

      socket.onmessage = (event) => {
        if (!active) return;
        try {
          const payload = JSON.parse(event.data);
          if (payload.type === "WIDGETS_SNAPSHOT" && Array.isArray(payload.widgets)) {
            setWidgets(payload.widgets);
          } else if (payload.type === "WIDGET_REGISTRY_EVENT") {
            fetchWidgets();
          }
        } catch {
        }
      };

      socket.onclose = () => {
        if (!active) return;
        setIsConnected(false);
        timer = setTimeout(connect, 3000);
      };

      socket.onerror = () => {
        if (socket) socket.close();
      };
    }

    connect();

    return () => {
      active = false;
      if (timer) clearTimeout(timer);
      if (socket) socket.close();
    };
  }, [fetchWidgets]);

  return {
    widgets,
    isConnected,
    isLoading,
    error,
    refresh: fetchWidgets,
    executeAction,
  };
}
