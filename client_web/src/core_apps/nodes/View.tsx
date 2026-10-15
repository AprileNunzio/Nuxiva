import React, { useEffect, useState } from 'react';
import {
  Server,
  Plus,
  Trash2,
  Cpu,
  Tv,
  Radio,
  Tablet,
  Usb,
  Terminal,
  CheckCircle2,
  Copy,
  ArrowRight,
  ArrowLeft,
  RefreshCw,
  Wifi,
  Key,
  ShieldCheck,
  X,
} from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { fetchNodes, fetchUsbPorts, onboardNode, deleteNode } from './api';
import { MeshNodeItem, UsbPort, HardwareTarget, OnboardResponse } from './types';

export const View: React.FC = () => {
  const { t } = useScopedI18n('core_apps/nodes');

  const [nodes, setNodes] = useState<MeshNodeItem[]>([]);
  const [usbPorts, setUsbPorts] = useState<UsbPort[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [showWizard, setShowWizard] = useState<boolean>(false);
  const [currentStep, setCurrentStep] = useState<number>(1);

  // Wizard state
  const [selectedTarget, setSelectedTarget] = useState<HardwareTarget>('esp32');
  const [selectedPort, setSelectedPort] = useState<string>('');
  const [nodeName, setNodeName] = useState<string>('');
  const [parentId, setParentId] = useState<string>('virtual_core');
  const [wifiSsid, setWifiSsid] = useState<string>('');
  const [wifiKey, setWifiKey] = useState<string>('');
  const [rootUser, setRootUser] = useState<string>('root');
  const [rootPass, setRootPass] = useState<string>('');
  const [flashing, setFlashing] = useState<boolean>(false);
  const [onboardResult, setOnboardResult] = useState<OnboardResponse | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  const loadData = async () => {
    try {
      setLoading(true);
      const [nodeList, portList] = await Promise.all([fetchNodes(), fetchUsbPorts()]);
      setNodes(nodeList);
      setUsbPorts(portList);
      if (portList.length > 0) {
        setSelectedPort(portList[0].device);
      }
    } catch (err) {
      console.error('Failed to load nodes data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleStartOnboard = async () => {
    try {
      setFlashing(true);
      const res = await onboardNode({
        target: selectedTarget,
        name: nodeName || `${selectedTarget.toUpperCase()}-Node`,
        parent_id: parentId,
        parent_ip: '127.0.0.1',
        usb_port: selectedPort,
        wifi_ssid: wifiSsid,
        wifi_key: wifiKey,
        root_user: rootUser,
        root_password: rootPass,
      });
      setOnboardResult(res);
      setCurrentStep(4);
      // Refresh fleet inventory
      const updatedNodes = await fetchNodes();
      setNodes(updatedNodes);
    } catch (err) {
      console.error('Onboarding failed:', err);
    } finally {
      setFlashing(false);
    }
  };

  const handleDeleteNode = async (nodeId: string) => {
    if (window.confirm(t('confirm_delete'))) {
      try {
        await deleteNode(nodeId);
        setNodes((prev) => prev.filter((n) => n.id !== nodeId));
      } catch (err) {
        console.error('Delete node failed:', err);
      }
    }
  };

  const handleCopyCommand = () => {
    const cmd = `curl -sSL https://get.nuxiva.local/install.sh | sudo bash -s -- --join 127.0.0.1 --token nux-auth-v5`;
    navigator.clipboard.writeText(cmd);
    setCopied(true);
    setTimeout(() => setCopied(false), 3000);
  };

  const resetWizard = () => {
    setShowWizard(false);
    setCurrentStep(1);
    setSelectedTarget('esp32');
    setNodeName('');
    setOnboardResult(null);
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 font-mono text-slate-100">
      {/* Fleet Overview Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-6 rounded-2xl border border-slate-800 bg-slate-900/70 backdrop-blur-xl shadow-lg">
        <div className="flex items-center gap-4">
          <div className="p-3 rounded-xl bg-cyan-500/10 border border-cyan-400/30 text-cyan-400 shadow-[0_0_15px_rgba(6,182,212,0.2)]">
            <Server className="w-8 h-8" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white">{t('title')}</h1>
            <p className="text-sm text-slate-400 mt-1">{t('description')}</p>
          </div>
        </div>

        <button
          onClick={() => {
            setShowWizard(true);
            setCurrentStep(1);
          }}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-slate-950 font-bold text-sm shadow-[0_0_25px_rgba(6,182,212,0.3)] transition-all"
        >
          <Plus className="w-4 h-4" />
          <span>{t('add_node')}</span>
        </button>
      </div>

      {/* Fleet Stats Banner */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800">
          <span className="text-xs text-slate-400 block">{t('total_nodes')}</span>
          <span className="text-2xl font-bold text-cyan-300 mt-1 block">{nodes.length}</span>
        </div>
        <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800">
          <span className="text-xs text-slate-400 block">{t('active_satellites')}</span>
          <span className="text-2xl font-bold text-indigo-300 mt-1 block">
            {nodes.filter((n) => n.type === 'satellite').length}
          </span>
        </div>
        <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800">
          <span className="text-xs text-slate-400 block">Porte USB Connesse</span>
          <span className="text-2xl font-bold text-emerald-300 mt-1 block">{usbPorts.length}</span>
        </div>
        <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800">
          <span className="text-xs text-slate-400 block">Mesh Protocol</span>
          <span className="text-xs font-bold text-purple-300 mt-2 block">Rust CRDT Gossip</span>
        </div>
      </div>

      {/* Fleet Inventory Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {loading ? (
          <div className="col-span-full py-16 flex items-center justify-center text-cyan-400">
            <RefreshCw className="w-8 h-8 animate-spin" />
          </div>
        ) : nodes.length === 0 ? (
          <div className="col-span-full py-12 text-center text-slate-500">Nessun nodo attivo.</div>
        ) : (
          nodes.map((node) => (
            <div
              key={node.id}
              className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-cyan-500/40 transition-all flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2.5">
                    <Server className="w-5 h-5 text-cyan-400" />
                    <span className="font-bold text-white text-sm truncate max-w-[170px]">
                      {node.name}
                    </span>
                  </div>
                  <span className="text-[10px] px-2.5 py-0.5 rounded-full uppercase font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                    Online
                  </span>
                </div>

                <div className="text-xs text-slate-400 space-y-1.5 mb-4">
                  <div>
                    <span className="text-slate-500">Tier: </span>
                    <span className="text-slate-300">{node.tier}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">IP: </span>
                    <span className="text-cyan-300">{node.ip}</span>
                  </div>
                  {node.parent_id && (
                    <div>
                      <span className="text-slate-500">Parent Link: </span>
                      <span className="text-indigo-300">{node.parent_id}</span>
                    </div>
                  )}
                  {node.telemetry && (
                    <div className="pt-2 border-t border-slate-800/80 flex items-center gap-3 text-[11px]">
                      <span className="text-slate-400">
                        CPU: {node.telemetry.cpu_percent?.toFixed(1) || 0}%
                      </span>
                      <span className="text-slate-400">
                        Temp: {node.telemetry.temp_c?.toFixed(1) || 0}°C
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {node.type === 'satellite' && (
                <button
                  onClick={() => handleDeleteNode(node.id)}
                  className="mt-3 w-full py-1.5 rounded-lg border border-red-500/30 text-red-400 hover:bg-red-500/10 text-xs font-semibold flex items-center justify-center gap-1.5 transition-all"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>{t('deprovision')}</span>
                </button>
              )}
            </div>
          ))
        )}
      </div>

      {/* Step-by-Step Onboarding Modal / Wizard Panel */}
      {showWizard && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
          <div className="relative w-full max-w-3xl rounded-2xl border border-cyan-500/40 bg-slate-950 p-6 shadow-[0_0_50px_rgba(6,182,212,0.25)] space-y-6">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div>
                <h2 className="text-xl font-bold text-white flex items-center gap-2">
                  <Usb className="w-5 h-5 text-cyan-400" />
                  <span>{t('wizard_title')}</span>
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">{t('wizard_subtitle')}</p>
              </div>
              <button
                onClick={resetWizard}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Step Indicators */}
            <div className="grid grid-cols-4 gap-2 text-center text-xs">
              {[1, 2, 3, 4].map((step) => (
                <div
                  key={step}
                  className={`py-2 rounded-lg font-bold border transition-all ${
                    currentStep === step
                      ? 'bg-cyan-500/20 text-cyan-300 border-cyan-400 shadow-[0_0_10px_rgba(6,182,212,0.3)]'
                      : currentStep > step
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                      : 'bg-slate-900 text-slate-500 border-slate-800'
                  }`}
                >
                  {t(`step_${step}` as any)}
                </div>
              ))}
            </div>

            {/* Step 1: Target Selection */}
            {currentStep === 1 && (
              <div className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div
                    onClick={() => setSelectedTarget('pc')}
                    className={`p-4 rounded-xl border cursor-pointer transition-all ${
                      selectedTarget === 'pc'
                        ? 'border-cyan-400 bg-cyan-950/40 shadow-[0_0_15px_rgba(6,182,212,0.25)]'
                        : 'border-slate-800 bg-slate-900/60 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center gap-2 text-cyan-400 mb-1">
                      <Cpu className="w-5 h-5" />
                      <span className="font-bold text-sm">{t('target_pc_title')}</span>
                    </div>
                    <p className="text-xs text-slate-400">{t('target_pc_desc')}</p>
                  </div>

                  <div
                    onClick={() => setSelectedTarget('raspberry')}
                    className={`p-4 rounded-xl border cursor-pointer transition-all ${
                      selectedTarget === 'raspberry'
                        ? 'border-indigo-400 bg-indigo-950/40 shadow-[0_0_15px_rgba(99,102,241,0.25)]'
                        : 'border-slate-800 bg-slate-900/60 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center gap-2 text-indigo-400 mb-1">
                      <Tv className="w-5 h-5" />
                      <span className="font-bold text-sm">{t('target_rpi_title')}</span>
                    </div>
                    <p className="text-xs text-slate-400">{t('target_rpi_desc')}</p>
                  </div>

                  <div
                    onClick={() => setSelectedTarget('esp32')}
                    className={`p-4 rounded-xl border cursor-pointer transition-all ${
                      selectedTarget === 'esp32'
                        ? 'border-emerald-400 bg-emerald-950/40 shadow-[0_0_15px_rgba(16,185,129,0.25)]'
                        : 'border-slate-800 bg-slate-900/60 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center gap-2 text-emerald-400 mb-1">
                      <Radio className="w-5 h-5" />
                      <span className="font-bold text-sm">{t('target_esp32_title')}</span>
                    </div>
                    <p className="text-xs text-slate-400">{t('target_esp32_desc')}</p>
                  </div>

                  <div
                    onClick={() => setSelectedTarget('android')}
                    className={`p-4 rounded-xl border cursor-pointer transition-all ${
                      selectedTarget === 'android'
                        ? 'border-purple-400 bg-purple-950/40 shadow-[0_0_15px_rgba(168,85,247,0.25)]'
                        : 'border-slate-800 bg-slate-900/60 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center gap-2 text-purple-400 mb-1">
                      <Tablet className="w-5 h-5" />
                      <span className="font-bold text-sm">{t('target_android_title')}</span>
                    </div>
                    <p className="text-xs text-slate-400">{t('target_android_desc')}</p>
                  </div>
                </div>

                <div className="flex justify-end pt-4">
                  <button
                    onClick={() => setCurrentStep(2)}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs transition-all"
                  >
                    <span>{t('next')}</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}

            {/* Step 2: Physical Link & Port Detection */}
            {currentStep === 2 && (
              <div className="space-y-4">
                {selectedTarget === 'pc' ? (
                  <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
                    <h3 className="text-sm font-bold text-white">{t('step2_pc_title')}</h3>
                    <p className="text-xs text-slate-400">{t('step2_pc_desc')}</p>
                    <div className="flex items-center gap-2 p-3 rounded-lg bg-black/80 border border-cyan-500/30 font-mono text-xs text-cyan-300">
                      <code className="flex-1 overflow-x-auto">
                        curl -sSL https://get.nuxiva.local/install.sh | sudo bash -s -- --join
                        127.0.0.1 --token nux-auth-v5
                      </code>
                      <button
                        onClick={handleCopyCommand}
                        className="px-3 py-1.5 rounded bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-400/40 text-[11px] font-bold flex items-center gap-1"
                      >
                        <Copy className="w-3.5 h-3.5" />
                        <span>{copied ? 'Copiato!' : t('copy_command')}</span>
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
                      <h3 className="text-sm font-bold text-white mb-1">{t('step2_usb_title')}</h3>
                      <p className="text-xs text-slate-400 mb-4">{t('step2_usb_desc')}</p>

                      <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                        {t('select_port')}
                      </label>
                      <select
                        value={selectedPort}
                        onChange={(e) => setSelectedPort(e.target.value)}
                        className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5 text-white font-mono text-xs focus:outline-none focus:border-cyan-400"
                      >
                        {usbPorts.map((p) => (
                          <option key={p.device} value={p.device}>
                            {p.device} - {p.description}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                )}

                <div className="flex justify-between pt-4">
                  <button
                    onClick={() => setCurrentStep(1)}
                    className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-all"
                  >
                    <ArrowLeft className="w-4 h-4" />
                    <span>{t('back')}</span>
                  </button>
                  <button
                    onClick={() => setCurrentStep(3)}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs transition-all"
                  >
                    <span>{t('next')}</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}

            {/* Step 3: Credentials & Routing */}
            {currentStep === 3 && (
              <div className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-semibold text-slate-300 block mb-1">
                      {t('node_name_label')}
                    </label>
                    <input
                      type="text"
                      placeholder="es. Micro-Salotto"
                      value={nodeName}
                      onChange={(e) => setNodeName(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-2 text-white font-mono text-xs focus:outline-none focus:border-cyan-400"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-slate-300 block mb-1">
                      {t('parent_node_label')}
                    </label>
                    <select
                      value={parentId}
                      onChange={(e) => setParentId(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-2 text-white font-mono text-xs focus:outline-none focus:border-cyan-400"
                    >
                      <option value="virtual_core">{t('virtual_core_option')}</option>
                      {nodes
                        .filter((n) => n.type === 'compute')
                        .map((n) => (
                          <option key={n.id} value={n.id}>
                            {n.name} ({n.ip})
                          </option>
                        ))}
                    </select>
                  </div>

                  {selectedTarget === 'esp32' && (
                    <>
                      <div>
                        <label className="text-xs font-semibold text-slate-300 block mb-1 flex items-center gap-1">
                          <Wifi className="w-3.5 h-3.5 text-cyan-400" />
                          <span>{t('wifi_ssid_label')}</span>
                        </label>
                        <input
                          type="text"
                          placeholder="Home_WiFi"
                          value={wifiSsid}
                          onChange={(e) => setWifiSsid(e.target.value)}
                          className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-2 text-white font-mono text-xs focus:outline-none focus:border-cyan-400"
                        />
                      </div>
                      <div>
                        <label className="text-xs font-semibold text-slate-300 block mb-1 flex items-center gap-1">
                          <Key className="w-3.5 h-3.5 text-indigo-400" />
                          <span>{t('wifi_key_label')}</span>
                        </label>
                        <input
                          type="password"
                          value={wifiKey}
                          onChange={(e) => setWifiKey(e.target.value)}
                          className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-2 text-white font-mono text-xs focus:outline-none focus:border-cyan-400"
                        />
                      </div>
                    </>
                  )}

                  {selectedTarget === 'raspberry' && (
                    <>
                      <div>
                        <label className="text-xs font-semibold text-slate-300 block mb-1">
                          {t('root_user_label')}
                        </label>
                        <input
                          type="text"
                          value={rootUser}
                          onChange={(e) => setRootUser(e.target.value)}
                          className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-2 text-white font-mono text-xs focus:outline-none focus:border-cyan-400"
                        />
                      </div>
                      <div>
                        <label className="text-xs font-semibold text-slate-300 block mb-1">
                          {t('root_pass_label')}
                        </label>
                        <input
                          type="password"
                          value={rootPass}
                          onChange={(e) => setRootPass(e.target.value)}
                          className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-2 text-white font-mono text-xs focus:outline-none focus:border-cyan-400"
                        />
                      </div>
                    </>
                  )}
                </div>

                <div className="flex justify-between pt-4">
                  <button
                    onClick={() => setCurrentStep(2)}
                    className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-all"
                  >
                    <ArrowLeft className="w-4 h-4" />
                    <span>{t('back')}</span>
                  </button>
                  <button
                    onClick={handleStartOnboard}
                    disabled={flashing}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-slate-950 font-bold text-xs transition-all shadow-[0_0_20px_rgba(6,182,212,0.3)] disabled:opacity-50"
                  >
                    <ShieldCheck className={`w-4 h-4 ${flashing ? 'animate-spin' : ''}`} />
                    <span>{flashing ? t('flashing_in_progress') : t('start_flashing')}</span>
                  </button>
                </div>
              </div>
            )}

            {/* Step 4: Output & Verification */}
            {currentStep === 4 && (
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 flex items-start gap-3">
                  <CheckCircle2 className="w-6 h-6 text-emerald-400 shrink-0" />
                  <div>
                    <h3 className="font-bold text-sm">{t('step4_success_title')}</h3>
                    <p className="text-xs text-emerald-400/80 mt-1">{t('step4_success_desc')}</p>
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-black border border-slate-800 font-mono text-xs space-y-2">
                  <div className="flex items-center gap-2 text-slate-400 pb-2 border-b border-slate-800">
                    <Terminal className="w-4 h-4 text-cyan-400" />
                    <span>{t('terminal_log')}</span>
                  </div>
                  <div className="text-cyan-400">[PROVISION] Dispositivo: {onboardResult?.name}</div>
                  <div className="text-slate-300">[TIER] {onboardResult?.tier}</div>
                  <div className="text-slate-400">[LOG] {onboardResult?.log}</div>
                  <div className="text-emerald-400">[STATUS] HANDSHAKE CRITTOGRAFICO COMPLETATO (P2P DIRECT STREAM READY)</div>
                </div>

                <div className="flex justify-end pt-4">
                  <button
                    onClick={resetWizard}
                    className="px-6 py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs transition-all"
                  >
                    {t('close_wizard')}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
