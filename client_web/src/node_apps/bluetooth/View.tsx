import React, { useState, useEffect } from 'react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import {
  Bluetooth,
  Radio,
  Headphones,
  Mouse,
  Smartphone,
  Save,
  CheckCircle2,
  Battery,
  Signal,
  RefreshCw,
  Search,
  Check,
  X,
} from 'lucide-react';

interface Props {
  nodeId?: string;
}

interface PairedDevice {
  mac: string;
  name: string;
  type: string;
  connected: boolean;
  battery?: number;
}

interface DiscoveredDevice {
  mac: string;
  name: string;
  type: string;
  rssi: number;
}

export const View: React.FC<Props> = ({ nodeId = 'node-01' }) => {
  const { t } = useScopedI18n('node_apps/bluetooth');

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  // Controller state
  const [powered, setPowered] = useState(true);
  const [discoverable, setDiscoverable] = useState(false);
  const [adapterInfo, setAdapterInfo] = useState({
    adapter: 'hci0',
    chipset: 'Intel Bluetooth 5.3 AX211 Controller',
    mac: 'F4:4D:30:8A:2B:1C',
  });

  // Devices
  const [pairedDevices, setPairedDevices] = useState<PairedDevice[]>([
    { mac: '70:26:05:AA:11:22', name: 'Sony WH-1000XM5', type: 'audio', connected: true, battery: 85 },
    { mac: 'DC:2C:26:BB:33:44', name: 'Logitech MX Master 3S', type: 'hid', connected: true, battery: 90 },
  ]);

  const [isScanning, setIsScanning] = useState(false);
  const [discoveredDevices, setDiscoveredDevices] = useState<DiscoveredDevice[]>([
    { mac: 'A4:C1:38:12:34:56', name: 'Xiaomi Mijia BLE Thermometer & Hygro', type: 'sensor', rssi: -58 },
    { mac: '58:24:AB:FE:DC:BA', name: 'Smart Ring Health Beacon', type: 'wearable', rssi: -72 },
  ]);

  useEffect(() => {
    let isMounted = true;
    const fetchHardware = async () => {
      try {
        setLoading(true);
        const res = await fetch(`/api/v5/nodes/${nodeId}/hardware`);
        if (res.ok) {
          const data = await res.json();
          if (isMounted && data.bluetooth) {
            setPowered(!!data.bluetooth.powered);
            setDiscoverable(!!data.bluetooth.discoverable);
            setAdapterInfo({
              adapter: data.bluetooth.adapter || 'hci0',
              chipset: data.bluetooth.chipset || 'Intel Bluetooth 5.3 AX211 Controller',
              mac: data.bluetooth.mac || 'F4:4D:30:8A:2B:1C',
            });
            if (Array.isArray(data.bluetooth.paired_devices)) {
              setPairedDevices(data.bluetooth.paired_devices);
            }
          }
        }
      } catch (err) {
        console.warn('Hardware fetch failed', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    fetchHardware();
    return () => {
      isMounted = false;
    };
  }, [nodeId]);

  const handleToggleScan = () => {
    if (isScanning) {
      setIsScanning(false);
    } else {
      setIsScanning(true);
      setTimeout(() => {
        setDiscoveredDevices((prev) => [
          ...prev,
          {
            mac: `00:1B:44:${Math.floor(Math.random() * 89 + 10)}:${Math.floor(Math.random() * 89 + 10)}:${Math.floor(Math.random() * 89 + 10)}`,
            name: 'Nuovo Dispositivo BLE Trovato',
            type: 'audio',
            rssi: -64,
          },
        ]);
        setIsScanning(false);
      }, 3500);
    }
  };

  const handlePairDiscovered = (dev: DiscoveredDevice) => {
    setPairedDevices((prev) => [
      ...prev,
      { mac: dev.mac, name: dev.name, type: dev.type, connected: true, battery: 100 },
    ]);
    setDiscoveredDevices((prev) => prev.filter((d) => d.mac !== dev.mac));
  };

  const handleToggleConnection = (mac: string) => {
    setPairedDevices((prev) =>
      prev.map((d) => (d.mac === mac ? { ...d, connected: !d.connected } : d))
    );
  };

  const handleForgetDevice = (mac: string) => {
    setPairedDevices((prev) => prev.filter((d) => d.mac !== mac));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await fetch(`/api/v5/nodes/${nodeId}/apps/bluetooth/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          enabled: powered,
          settings: {
            powered,
            discoverable,
            paired_devices: pairedDevices,
          },
        }),
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const getDeviceIcon = (type: string) => {
    switch (type) {
      case 'audio':
        return <Headphones className="w-4 h-4 text-cyan-400" />;
      case 'hid':
        return <Mouse className="w-4 h-4 text-purple-400" />;
      default:
        return <Smartphone className="w-4 h-4 text-emerald-400" />;
    }
  };

  if (loading) {
    return (
      <div className="p-12 flex flex-col items-center justify-center text-slate-400 font-mono gap-3">
        <RefreshCw className="w-6 h-6 animate-spin text-cyan-400" />
        <span className="text-xs">Rilevamento radio Bluetooth del nodo...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6 font-mono text-slate-100">
      {/* Header */}
      <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-xl">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
            <Bluetooth className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white tracking-wide">{t('title')}</h2>
            <p className="text-xs text-slate-400 mt-0.5">{t('description')}</p>
          </div>
        </div>

        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-cyan-500/20 transition cursor-pointer"
        >
          {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          {saving ? t('saving') : t('save')}
        </button>
      </div>

      {saved && (
        <div className="bg-emerald-950/60 border border-emerald-500/40 p-3.5 rounded-xl flex items-center gap-3 text-xs text-emerald-300">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{t('saved')}</span>
        </div>
      )}

      {/* Controller & Radio Status */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-4">
        <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
          <Radio className="w-4 h-4 text-cyan-400" />
          {t('adapter_title')}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-slate-950 border border-slate-800 p-4 rounded-xl">
            <div className="text-[11px] text-slate-400">Chipset & Adapter</div>
            <div className="text-xs font-bold text-white mt-1">{adapterInfo.chipset}</div>
            <div className="text-[10px] text-slate-500 mt-0.5">Interface: {adapterInfo.adapter} · MAC: {adapterInfo.mac}</div>
          </div>

          <div
            onClick={() => setPowered(!powered)}
            className={`p-4 rounded-xl border cursor-pointer transition flex items-center justify-between ${
              powered ? 'bg-cyan-950/20 border-cyan-500/50' : 'bg-slate-950 border-slate-800'
            }`}
          >
            <div>
              <div className="text-xs font-bold text-white">{t('powered_toggle')}</div>
              <div className="text-[10px] text-slate-400 mt-0.5">Trasmettitore RF 2.4 GHz</div>
            </div>
            <span className={`text-xs font-bold ${powered ? 'text-cyan-400' : 'text-slate-500'}`}>
              {powered ? 'ATTIVO' : 'SPENTO'}
            </span>
          </div>

          <div
            onClick={() => setDiscoverable(!discoverable)}
            className={`p-4 rounded-xl border cursor-pointer transition flex items-center justify-between ${
              discoverable ? 'bg-purple-950/20 border-purple-500/50' : 'bg-slate-950 border-slate-800'
            }`}
          >
            <div>
              <div className="text-xs font-bold text-white">{t('discoverable_toggle')}</div>
              <div className="text-[10px] text-slate-400 mt-0.5">Visibilità per associazione</div>
            </div>
            <span className={`text-xs font-bold ${discoverable ? 'text-purple-400' : 'text-slate-500'}`}>
              {discoverable ? 'VISIBILE' : 'NASCOSTO'}
            </span>
          </div>
        </div>
      </div>

      {/* Paired Devices */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-4">
        <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Bluetooth className="w-4 h-4 text-cyan-400" />
            {t('paired_title')}
          </span>
          <span className="text-[10px] text-slate-500">{pairedDevices.length} accoppiati</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {pairedDevices.map((dev) => (
            <div key={dev.mac} className="bg-slate-950 border border-slate-800 p-4 rounded-xl flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                  {getDeviceIcon(dev.type)}
                </div>
                <div>
                  <div className="text-xs font-bold text-white">{dev.name}</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">
                    MAC: {dev.mac}
                    {dev.battery !== undefined && (
                      <span className="ml-2 text-emerald-400 inline-flex items-center gap-1">
                        <Battery className="w-3 h-3" /> {dev.battery}%
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleToggleConnection(dev.mac)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                    dev.connected
                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                      : 'bg-slate-800 text-slate-400 hover:text-white'
                  }`}
                >
                  {dev.connected ? t('connected') : t('disconnect')}
                </button>
                <button
                  onClick={() => handleForgetDevice(dev.mac)}
                  className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-slate-900 transition"
                  title={t('forget')}
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Real-Time BLE Scanner */}
      <div className="bg-slate-950 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div>
            <div className="text-xs font-semibold text-cyan-400 flex items-center gap-2">
              <Search className="w-4 h-4" />
              {t('scan_title')}
            </div>
            <p className="text-xs text-slate-400 mt-0.5">Rileva sensori BLE, beacon e dispositivi audio nelle vicinanze</p>
          </div>

          <button
            onClick={handleToggleScan}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition shadow-lg cursor-pointer ${
              isScanning
                ? 'bg-rose-600 text-white animate-pulse'
                : 'bg-cyan-600 hover:bg-cyan-500 text-white shadow-cyan-600/20'
            }`}
          >
            {isScanning ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
            {isScanning ? t('scanning') : t('start_scan')}
          </button>
        </div>

        {discoveredDevices.length === 0 ? (
          <div className="text-xs text-slate-500 text-center py-6">{t('no_devices')}</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {discoveredDevices.map((dev) => (
              <div key={dev.mac} className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl flex items-center justify-between">
                <div>
                  <div className="text-xs font-bold text-white">{dev.name}</div>
                  <div className="text-[10px] text-slate-400 mt-0.5 flex items-center gap-2">
                    <span>{dev.mac}</span>
                    <span className="text-cyan-400 flex items-center gap-1">
                      <Signal className="w-3 h-3" /> {dev.rssi} dBm
                    </span>
                  </div>
                </div>

                <button
                  onClick={() => handlePairDiscovered(dev)}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-300 border border-cyan-500/40 rounded-lg text-xs font-semibold transition"
                >
                  <Check className="w-3.5 h-3.5" />
                  {t('pair_btn')}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default View;
