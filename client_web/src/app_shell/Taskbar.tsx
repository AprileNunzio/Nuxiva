import React, { useEffect, useState } from 'react';
import { Grid2X2, UserRound, Activity, X, Wifi, WifiOff, Network, Bluetooth, Waypoints } from 'lucide-react';
import { appRegistry } from './window_manager/registry';
import { windowStore } from './window_manager/WindowStore';
import type { OSWindow } from './window_manager/types';
import { useScopedI18n, getScopedString } from '../shared/i18n/useScopedI18n';
import { OSIcon3D } from './OSIcon3D';
import { taskbarGroups } from './taskbarGroups';
import { useAssistantIdentity } from '../shared/identity/IdentityContext';
import { useNetworkState } from './tray/network/useNetworkState';
import { useBluetoothState } from './tray/bluetooth/useBluetoothState';
import { useHardwareCapabilities } from './hardware/useHardwareCapabilities';
import { fetchNodes } from '../core_apps/nodes/api';
import type { MeshNodeItem } from '../core_apps/nodes/types';
import './taskbar.css';

export function Taskbar({
  user,
  userMenu,
  onUserMenu,
  windows,
  launcher,
  onStart,
  onOpen,
  clock,
  calendar,
  onCalendar,
  network = false,
  onNetwork,
  bluetooth = false,
  onBluetooth,
}: {
  user: string;
  userMenu: boolean;
  onUserMenu: () => void;
  windows: OSWindow[];
  launcher: boolean;
  onStart: () => void;
  onOpen: (id: string, newInstance?: boolean) => void;
  clock: Date;
  calendar: boolean;
  onCalendar: () => void;
  network?: boolean;
  onNetwork?: () => void;
  bluetooth?: boolean;
  onBluetooth?: () => void;
}) {
  const { t, lang } = useScopedI18n('app_shell');
  const assistant = useAssistantIdentity();
  const [group, setGroup] = useState<string | null>(null);
  const groups = taskbarGroups(windows, []);
  const [nodes, setNodes] = useState<MeshNodeItem[] | null>(null);
  const [context, setContext] = useState<{ x: number; nodeId?: string } | null>(null);
  const localNode = nodes?.find(node => node.source === 'local');
  const connectedCount = nodes ? new Set(nodes.filter(node => node.online === true).map(node => node.id)).size : null;

  useEffect(() => {
    let disposed = false;
    const refresh = async () => {
      try {
        const result = await fetchNodes();
        if (!disposed) setNodes(result);
      } catch {
        if (!disposed) setNodes(null);
      }
    };
    void refresh();
    const timer = window.setInterval(() => { void refresh(); }, 10000);
    return () => { disposed = true; window.clearInterval(timer); };
  }, []);
  const selected = groups.find(item => item.appId === group);
  const networkState = useNetworkState();
  const bluetoothState = useBluetoothState();
  const hardwareAvailable = useHardwareCapabilities();
  const wifiAvailable = hardwareAvailable('network.wifi') ?? networkState.isWifiAvailable;
  const bluetoothAvailable = hardwareAvailable('bluetooth.controller') ?? bluetoothState.isAvailable;

  const title = (id: string) => {
    if (id === 'explorer') return assistant.name;
    const app = appRegistry.find(a => a.id === id);
    return app ? getScopedString(app.scope, lang, 'title', app.name) : id;
  };

  useEffect(() => {
    const close = (event: PointerEvent) => {
      if (!(event.target as Element).closest('.os-taskbar')) { setGroup(null); setContext(null); }
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { setGroup(null); setContext(null); }
    };
    window.addEventListener('pointerdown', close);
    window.addEventListener('keydown', escape);
    return () => {
      window.removeEventListener('pointerdown', close);
      window.removeEventListener('keydown', escape);
    };
  }, []);

  const icon = (item: typeof groups[number]) => {
    const app = appRegistry.find(a => a.id === item.appId);
    if (!app) return null;
    return (
      <button
        key={item.appId}
        className="os-task-button"
        title={title(app.id)}
        aria-label={title(app.id)}
        aria-expanded={item.entries.length > 1 ? group === app.id : undefined}
        data-running={item.entries.length > 0}
        onContextMenu={event => {
          event.preventDefault();
          event.stopPropagation();
          setGroup(null);
          const active = item.entries.find(entry => !entry.minimized) || item.entries[0];
          setContext({ x: event.clientX, nodeId: active?.targetNodeId || localNode?.id });
        }}
        onClick={event => {
          if (event.shiftKey) {
            onOpen(app.id, true);
            return;
          }
          if (item.entries.length > 1) {
            setGroup(group === app.id ? null : app.id);
            return;
          }
          const entry = item.entries[0];
          if (!entry) {
            onOpen(app.id);
            return;
          }
          const active = windows.filter(w => !w.minimized).sort((a, b) => b.z - a.z)[0];
          if (active?.id === entry.id) windowStore.update(entry.id, { minimized: true });
          else windowStore.focus(entry.id);
          setGroup(null);
        }}
      >
        <OSIcon3D name={app.name} source={app.iconUrl} />
        {item.entries.length > 1 && <span className="os-task-count">{item.entries.length}</span>}
      </button>
    );
  };

  return (
    <footer className="os-taskbar" onContextMenu={event => {
      event.preventDefault();
      setGroup(null);
      setContext({ x: event.clientX, nodeId: localNode?.id });
    }} onClick={event => {
      if (!(event.target as Element).closest('.os-task-context')) setContext(null);
    }}>
      <button className="os-task-user" title={user} aria-label={t('signed_in_as', { user })}
        aria-expanded={userMenu} aria-haspopup="dialog"
        onClick={() => { setGroup(null); onUserMenu(); }}>
        <UserRound aria-hidden="true" /><span>{user}</span>
      </button>
      <nav className="os-task-apps" aria-label={t('os_windows')}>
        <button
          className="os-task-button"
          data-os-start
          aria-label={t('os_applications')}
          title={t('os_applications')}
          aria-expanded={launcher}
          onClick={() => {
            setGroup(null);
            onStart();
          }}
        >
          <Grid2X2 />
        </button>
        {groups.map(icon)}
      </nav>

      <div className="os-task-tray">

        <div className="os-task-tray-group">
          {onNetwork && (
            <>
              {(!wifiAvailable || networkState.hasEthernet) && (
                <button
                  className="os-task-tray-button os-task-tray-network"
                  aria-label={t('os_network') || 'Rete'}
                  title={networkState.isConnected ? 'Ethernet' : 'Offline'}
                  aria-expanded={network}
                  onClick={() => {
                    setGroup(null);
                    onNetwork();
                  }}
                >
                  {!networkState.isConnected ? <WifiOff size={16} /> : <Network size={16} />}
                </button>
              )}

              {wifiAvailable && (
                <button
                  className="os-task-tray-button os-task-tray-wifi"
                  aria-label="Wi-Fi"
                  title={networkState.isWifiActive ? (networkState.wifi?.current_ssid || 'Wi-Fi') : 'Wi-Fi'}
                  aria-expanded={network}
                  onClick={() => {
                    setGroup(null);
                    onNetwork();
                  }}
                >
                  <Wifi size={16} />
                </button>
              )}
            </>
          )}

          {onBluetooth && bluetoothAvailable && (
            <button
              className="os-task-tray-button os-task-tray-bluetooth"
              aria-label={t('os_bluetooth') || 'Bluetooth'}
              title={bluetoothState.isPowered ? 'Bluetooth' : 'Bluetooth off'}
              aria-expanded={bluetooth}
              onClick={() => {
                setGroup(null);
                onBluetooth();
              }}
            >
              <Bluetooth size={16} />
            </button>
          )}
        </div>

        <button className="os-task-tray-button os-task-nodes"
          title={t(nodes ? 'os_connected_nodes' : 'os_nodes_unavailable', { count: connectedCount ?? '—' })}
          aria-label={t(nodes ? 'os_connected_nodes' : 'os_nodes_unavailable', { count: connectedCount ?? '—' })}
          onClick={() => { setGroup(null); onOpen('nodes'); }}>
          <Waypoints aria-hidden="true" /><span>{connectedCount ?? '—'}</span>
        </button>
        <button
          className="os-task-clock"
          aria-label={t('os_calendar')}
          aria-expanded={calendar}
          onClick={() => {
            setGroup(null);
            onCalendar();
          }}
        >
          <time>{clock.toLocaleTimeString(lang, { hour: '2-digit', minute: '2-digit' })}</time>
          <span>{clock.toLocaleDateString(lang, { day: '2-digit', month: '2-digit', year: 'numeric' })}</span>
        </button>
      </div>

      {context && (
        <div className="os-task-context" role="menu" style={{ left: Math.max(8, Math.min(context.x, window.innerWidth - 250)) }}>
          <button role="menuitem" onClick={() => {
            windowStore.openWindow({ appId: 'task_manager', targetNodeId: context.nodeId || 'virtual_core' });
            setContext(null);
          }}><Activity aria-hidden="true" />{title('task_manager')}</button>
        </div>
      )}
      {selected && (
        <div className="os-task-switcher" role="dialog" aria-label={title(selected.appId)}>
          <strong>{title(selected.appId)}</strong>
          {selected.entries.map(entry => (
            <div key={entry.id} onContextMenu={event => {
              event.preventDefault();
              event.stopPropagation();
              setGroup(null);
              setContext({ x: event.clientX, nodeId: entry.targetNodeId || localNode?.id });
            }}>
              <button
                onClick={() => {
                  windowStore.focus(entry.id);
                  setGroup(null);
                }}
              >
                {title(entry.appId)}
                {entry.targetNodeId ? ` · ${entry.targetNodeId}` : ''}
              </button>
              <button
                aria-label={t('os_close')}
                title={t('os_close')}
                onClick={() => windowStore.close(entry.id)}
              >
                <X />
              </button>
            </div>
          ))}
          <button
            onClick={() => {
              onOpen(selected.appId, true);
              setGroup(null);
            }}
          >
            {t('os_new_window')}
          </button>
        </div>
      )}
    </footer>
  );
}
