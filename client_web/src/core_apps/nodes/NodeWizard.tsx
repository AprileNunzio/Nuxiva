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
import { fetchNodes, onboardNode } from './api';
import { MeshNodeItem, UsbPort, HardwareTarget, OnboardResponse } from './types';
import { PcLinkPanel } from './components/PcLinkPanel';
import { reportError } from '../../shared/errors/errorBus';
import { LinksHandle } from '../../node_apps/client_link/hooks/useLinks';

interface Props { nodes: MeshNodeItem[]; usbPorts: UsbPort[]; links: LinksHandle; onChanged: (nodes: MeshNodeItem[]) => void; onClose: () => void; }

export const NodeWizard: React.FC<Props> = ({ nodes, usbPorts, links, onChanged, onClose }) => {
  const { t } = useScopedI18n('core_apps/nodes');
  const [currentStep, setCurrentStep] = useState<number>(1);

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
      const updatedNodes = await fetchNodes();
      onChanged(updatedNodes);
    } catch (err) {
      reportError('nodes_onboard_failed', err);
    } finally {
      setFlashing(false);
    }
  };

  const resetWizard = () => onClose();

  return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 overflow-y-auto bg-black/80 backdrop-blur-md">
          <div className="relative my-auto max-h-[90dvh] overflow-y-auto w-full max-w-3xl rounded-2xl border border-cyan-300 bg-white p-6 shadow-[0_0_50px_rgba(6,182,212,0.25)] space-y-6">

            <div className="flex items-center justify-between border-b border-slate-200 pb-4">
              <div>
                <h2 className="text-xl font-bold text-slate-950 flex items-center gap-2">
                  <Usb className="w-5 h-5 text-cyan-600" />
                  <span>{t('wizard_title')}</span>
                </h2>
                <p className="text-xs text-slate-600 mt-0.5">{t('wizard_subtitle')}</p>
              </div>
              <button
                onClick={resetWizard}
                className="p-1 rounded-lg text-slate-600 hover:text-slate-950 hover:bg-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="grid grid-cols-4 gap-2 text-center text-xs">
              {[1, 2, 3, 4].map((step) => (
                <div
                  key={step}
                  className={`py-2 rounded-lg font-bold border transition-all ${
                    currentStep === step
                      ? 'bg-cyan-100 text-cyan-700 border-cyan-400 shadow-[0_0_10px_rgba(6,182,212,0.3)]'
                      : currentStep > step
                      ? 'bg-emerald-50 text-emerald-600 border-emerald-300'
                      : 'bg-white text-slate-500 border-slate-200'
                  }`}
                >
                  {t(`step_${step}` as any)}
                </div>
              ))}
            </div>

            {currentStep === 1 && (
              <div className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div
                    onClick={() => setSelectedTarget('pc')}
                    className={`p-4 rounded-xl border cursor-pointer transition-all ${
                      selectedTarget === 'pc'
                        ? 'border-cyan-400 bg-cyan-950/40 shadow-[0_0_15px_rgba(6,182,212,0.25)]'
                        : 'border-slate-200 bg-white hover:border-slate-300'
                    }`}
                  >
                    <div className="flex items-center gap-2 text-cyan-600 mb-1">
                      <Cpu className="w-5 h-5" />
                      <span className="font-bold text-sm">{t('target_pc_title')}</span>
                    </div>
                    <p className="text-xs text-slate-600">{t('target_pc_desc')}</p>
                  </div>

                  <div
                    onClick={() => setSelectedTarget('raspberry')}
                    className={`p-4 rounded-xl border cursor-pointer transition-all ${
                      selectedTarget === 'raspberry'
                        ? 'border-indigo-400 bg-indigo-950/40 shadow-[0_0_15px_rgba(99,102,241,0.25)]'
                        : 'border-slate-200 bg-white hover:border-slate-300'
                    }`}
                  >
                    <div className="flex items-center gap-2 text-indigo-600 mb-1">
                      <Tv className="w-5 h-5" />
                      <span className="font-bold text-sm">{t('target_rpi_title')}</span>
                    </div>
                    <p className="text-xs text-slate-600">{t('target_rpi_desc')}</p>
                  </div>

                  <div
                    onClick={() => setSelectedTarget('esp32')}
                    className={`p-4 rounded-xl border cursor-pointer transition-all ${
                      selectedTarget === 'esp32'
                        ? 'border-emerald-400 bg-emerald-950/40 shadow-[0_0_15px_rgba(16,185,129,0.25)]'
                        : 'border-slate-200 bg-white hover:border-slate-300'
                    }`}
                  >
                    <div className="flex items-center gap-2 text-emerald-600 mb-1">
                      <Radio className="w-5 h-5" />
                      <span className="font-bold text-sm">{t('target_esp32_title')}</span>
                    </div>
                    <p className="text-xs text-slate-600">{t('target_esp32_desc')}</p>
                  </div>

                  <div
                    onClick={() => setSelectedTarget('android')}
                    className={`p-4 rounded-xl border cursor-pointer transition-all ${
                      selectedTarget === 'android'
                        ? 'border-purple-400 bg-purple-950/40 shadow-[0_0_15px_rgba(168,85,247,0.25)]'
                        : 'border-slate-200 bg-white hover:border-slate-300'
                    }`}
                  >
                    <div className="flex items-center gap-2 text-purple-600 mb-1">
                      <Tablet className="w-5 h-5" />
                      <span className="font-bold text-sm">{t('target_android_title')}</span>
                    </div>
                    <p className="text-xs text-slate-600">{t('target_android_desc')}</p>
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

            {currentStep === 2 && (
              <div className="space-y-4">
                {selectedTarget === 'pc' ? (
                  <PcLinkPanel handle={links} />
                ) : (
                  <div className="space-y-3">
                    <div className="p-4 rounded-xl bg-white border border-slate-200">
                      <h3 className="text-sm font-bold text-slate-950 mb-1">{t('step2_usb_title')}</h3>
                      <p className="text-xs text-slate-600 mb-4">{t('step2_usb_desc')}</p>

                      <label className="text-xs font-semibold text-slate-700 block mb-1.5">
                        {t('select_port')}
                      </label>
                      <select
                        value={selectedPort}
                        onChange={(e) => setSelectedPort(e.target.value)}
                        className="w-full bg-slate-100 border border-slate-300 rounded-xl px-4 py-2.5 text-slate-950 font-mono text-xs focus:outline-none focus:border-cyan-400"
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
                    className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition-all"
                  >
                    <ArrowLeft className="w-4 h-4" />
                    <span>{t('back')}</span>
                  </button>
                  <button
                    disabled={selectedTarget === 'pc'}
                    onClick={() => setCurrentStep(3)}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs transition-all"
                  >
                    <span>{t('next')}</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}

            {currentStep === 3 && (
              <div className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-semibold text-slate-700 block mb-1">
                      {t('node_name_label')}
                    </label>
                    <input
                      type="text"
                      placeholder="es. Micro-Salotto"
                      value={nodeName}
                      onChange={(e) => setNodeName(e.target.value)}
                      className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-slate-950 font-mono text-xs focus:outline-none focus:border-cyan-400"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-slate-700 block mb-1">
                      {t('parent_node_label')}
                    </label>
                    <select
                      value={parentId}
                      onChange={(e) => setParentId(e.target.value)}
                      className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-slate-950 font-mono text-xs focus:outline-none focus:border-cyan-400"
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
                        <label className="text-xs font-semibold text-slate-700 block mb-1 flex items-center gap-1">
                          <Wifi className="w-3.5 h-3.5 text-cyan-600" />
                          <span>{t('wifi_ssid_label')}</span>
                        </label>
                        <input
                          type="text"
                          placeholder="Home_WiFi"
                          value={wifiSsid}
                          onChange={(e) => setWifiSsid(e.target.value)}
                          className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-slate-950 font-mono text-xs focus:outline-none focus:border-cyan-400"
                        />
                      </div>
                      <div>
                        <label className="text-xs font-semibold text-slate-700 block mb-1 flex items-center gap-1">
                          <Key className="w-3.5 h-3.5 text-indigo-600" />
                          <span>{t('wifi_key_label')}</span>
                        </label>
                        <input
                          type="password"
                          value={wifiKey}
                          onChange={(e) => setWifiKey(e.target.value)}
                          className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-slate-950 font-mono text-xs focus:outline-none focus:border-cyan-400"
                        />
                      </div>
                    </>
                  )}

                  {selectedTarget === 'raspberry' && (
                    <>
                      <div>
                        <label className="text-xs font-semibold text-slate-700 block mb-1">
                          {t('root_user_label')}
                        </label>
                        <input
                          type="text"
                          value={rootUser}
                          onChange={(e) => setRootUser(e.target.value)}
                          className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-slate-950 font-mono text-xs focus:outline-none focus:border-cyan-400"
                        />
                      </div>
                      <div>
                        <label className="text-xs font-semibold text-slate-700 block mb-1">
                          {t('root_pass_label')}
                        </label>
                        <input
                          type="password"
                          value={rootPass}
                          onChange={(e) => setRootPass(e.target.value)}
                          className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-slate-950 font-mono text-xs focus:outline-none focus:border-cyan-400"
                        />
                      </div>
                    </>
                  )}
                </div>

                <div className="flex justify-between pt-4">
                  <button
                    onClick={() => setCurrentStep(2)}
                    className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition-all"
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

            {currentStep === 4 && (
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-300 text-emerald-700 flex items-start gap-3">
                  <CheckCircle2 className="w-6 h-6 text-emerald-600 shrink-0" />
                  <div>
                    <h3 className="font-bold text-sm">{t('step4_success_title')}</h3>
                    <p className="text-xs text-emerald-600 mt-1">{t('step4_success_desc')}</p>
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-black border border-slate-200 font-mono text-xs space-y-2">
                  <div className="flex items-center gap-2 text-slate-600 pb-2 border-b border-slate-200">
                    <Terminal className="w-4 h-4 text-cyan-600" />
                    <span>{t('terminal_log')}</span>
                  </div>
                  <div className="text-cyan-600">[PROVISION] Dispositivo: {onboardResult?.name}</div>
                  <div className="text-slate-700">[TIER] {onboardResult?.tier}</div>
                  <div className="text-slate-600">[LOG] {onboardResult?.log}</div>
                  <div className="text-emerald-600">[STATUS] HANDSHAKE CRITTOGRAFICO COMPLETATO (P2P DIRECT STREAM READY)</div>
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
  );
};
