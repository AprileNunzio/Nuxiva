import React, { useState } from 'react';
import {
  Cpu,
  Tv,
  Radio,
  Tablet,
  Usb,
  Terminal,
  CheckCircle2,
  ArrowRight,
  ArrowLeft,
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

interface Props {
  readonly nodes: MeshNodeItem[];
  readonly usbPorts: UsbPort[];
  readonly links: LinksHandle;
  readonly onChanged: (nodes: MeshNodeItem[]) => void;
  readonly onClose: () => void;
}

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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 overflow-y-auto bg-slate-950/75 backdrop-blur-md animate-fadeIn">
      <div className="relative my-auto max-h-[90dvh] overflow-y-auto w-full max-w-3xl rounded-3xl border border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/95 p-6 sm:p-7 shadow-2xl space-y-6">
        <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-4">
          <div>
            <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <Usb className="w-5 h-5 text-cyan-600 dark:text-cyan-400" />
              <span>{t('wizard_title')}</span>
            </h2>
            <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">{t('wizard_subtitle')}</p>
          </div>
          <button
            onClick={resetWizard}
            className="p-1.5 rounded-xl text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="grid grid-cols-4 gap-2 text-center text-xs">
          {[1, 2, 3, 4].map((step) => (
            <div
              key={step}
              className={`py-2 rounded-xl font-bold border transition-all ${
                currentStep === step
                  ? 'bg-cyan-50 dark:bg-cyan-950/40 text-cyan-700 dark:text-cyan-300 border-cyan-400 shadow-sm'
                  : currentStep > step
                  ? 'bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-300 border-emerald-300 dark:border-emerald-800'
                  : 'bg-slate-50 dark:bg-slate-800/40 text-slate-500 border-slate-200 dark:border-slate-800'
              }`}
            >
              {t(`step_${step}` as any)}
            </div>
          ))}
        </div>

        {currentStep === 1 && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              <div
                onClick={() => setSelectedTarget('pc')}
                className={`p-4 rounded-2xl border cursor-pointer transition-all ${
                  selectedTarget === 'pc'
                    ? 'border-cyan-400 bg-cyan-500/10 shadow-[0_0_15px_rgba(6,182,212,0.15)] ring-2 ring-cyan-400/50'
                    : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-800/50 hover:border-slate-300 dark:hover:border-slate-700'
                }`}
              >
                <div className="flex items-center gap-2 text-cyan-600 dark:text-cyan-400 mb-1">
                  <Cpu className="w-5 h-5" />
                  <span className="font-bold text-sm text-slate-900 dark:text-slate-100">{t('target_pc_title')}</span>
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-400">{t('target_pc_desc')}</p>
              </div>

              <div
                onClick={() => setSelectedTarget('raspberry')}
                className={`p-4 rounded-2xl border cursor-pointer transition-all ${
                  selectedTarget === 'raspberry'
                    ? 'border-indigo-400 bg-indigo-500/10 shadow-[0_0_15px_rgba(99,102,241,0.15)] ring-2 ring-indigo-400/50'
                    : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-800/50 hover:border-slate-300 dark:hover:border-slate-700'
                }`}
              >
                <div className="flex items-center gap-2 text-indigo-600 dark:text-indigo-400 mb-1">
                  <Tv className="w-5 h-5" />
                  <span className="font-bold text-sm text-slate-900 dark:text-slate-100">{t('target_rpi_title')}</span>
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-400">{t('target_rpi_desc')}</p>
              </div>

              <div
                onClick={() => setSelectedTarget('esp32')}
                className={`p-4 rounded-2xl border cursor-pointer transition-all ${
                  selectedTarget === 'esp32'
                    ? 'border-emerald-400 bg-emerald-500/10 shadow-[0_0_15px_rgba(16,185,129,0.15)] ring-2 ring-emerald-400/50'
                    : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-800/50 hover:border-slate-300 dark:hover:border-slate-700'
                }`}
              >
                <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 mb-1">
                  <Radio className="w-5 h-5" />
                  <span className="font-bold text-sm text-slate-900 dark:text-slate-100">{t('target_esp32_title')}</span>
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-400">{t('target_esp32_desc')}</p>
              </div>

              <div
                onClick={() => setSelectedTarget('android')}
                className={`p-4 rounded-2xl border cursor-pointer transition-all ${
                  selectedTarget === 'android'
                    ? 'border-purple-400 bg-purple-500/10 shadow-[0_0_15px_rgba(168,85,247,0.15)] ring-2 ring-purple-400/50'
                    : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-800/50 hover:border-slate-300 dark:hover:border-slate-700'
                }`}
              >
                <div className="flex items-center gap-2 text-purple-600 dark:text-purple-400 mb-1">
                  <Tablet className="w-5 h-5" />
                  <span className="font-bold text-sm text-slate-900 dark:text-slate-100">{t('target_android_title')}</span>
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-400">{t('target_android_desc')}</p>
              </div>
            </div>

            <div className="flex justify-end pt-4">
              <button
                onClick={() => setCurrentStep(2)}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 active:scale-[0.99] text-white font-bold text-xs transition-all shadow-sm"
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
                <div className="p-4 rounded-2xl bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800">
                  <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 mb-1">{t('step2_usb_title')}</h3>
                  <p className="text-xs text-slate-600 dark:text-slate-400 mb-4">{t('step2_usb_desc')}</p>

                  <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1.5">
                    {t('select_port')}
                  </label>
                  <select
                    value={selectedPort}
                    onChange={(e) => setSelectedPort(e.target.value)}
                    className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl px-4 py-2.5 text-slate-900 dark:text-slate-100 font-mono text-xs focus:outline-none focus:border-cyan-400"
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
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-semibold transition-all"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>{t('back')}</span>
              </button>
              <button
                disabled={selectedTarget === 'pc'}
                onClick={() => setCurrentStep(3)}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 active:scale-[0.99] text-white font-bold text-xs transition-all shadow-sm disabled:opacity-50"
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
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                  {t('node_name_label')}
                </label>
                <input
                  type="text"
                  placeholder="es. Micro-Salotto"
                  value={nodeName}
                  onChange={(e) => setNodeName(e.target.value)}
                  className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl px-4 py-2 text-slate-900 dark:text-slate-100 font-mono text-xs focus:outline-none focus:border-cyan-400"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                  {t('parent_node_label')}
                </label>
                <select
                  value={parentId}
                  onChange={(e) => setParentId(e.target.value)}
                  className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl px-4 py-2 text-slate-900 dark:text-slate-100 font-mono text-xs focus:outline-none focus:border-cyan-400"
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
                    <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1 flex items-center gap-1">
                      <Wifi className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
                      <span>{t('wifi_ssid_label')}</span>
                    </label>
                    <input
                      type="text"
                      placeholder="Home_WiFi"
                      value={wifiSsid}
                      onChange={(e) => setWifiSsid(e.target.value)}
                      className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl px-4 py-2 text-slate-900 dark:text-slate-100 font-mono text-xs focus:outline-none focus:border-cyan-400"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1 flex items-center gap-1">
                      <Key className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
                      <span>{t('wifi_key_label')}</span>
                    </label>
                    <input
                      type="password"
                      value={wifiKey}
                      onChange={(e) => setWifiKey(e.target.value)}
                      className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl px-4 py-2 text-slate-900 dark:text-slate-100 font-mono text-xs focus:outline-none focus:border-cyan-400"
                    />
                  </div>
                </>
              )}

              {selectedTarget === 'raspberry' && (
                <>
                  <div>
                    <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                      {t('root_user_label')}
                    </label>
                    <input
                      type="text"
                      value={rootUser}
                      onChange={(e) => setRootUser(e.target.value)}
                      className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl px-4 py-2 text-slate-900 dark:text-slate-100 font-mono text-xs focus:outline-none focus:border-cyan-400"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                      {t('root_pass_label')}
                    </label>
                    <input
                      type="password"
                      value={rootPass}
                      onChange={(e) => setRootPass(e.target.value)}
                      className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl px-4 py-2 text-slate-900 dark:text-slate-100 font-mono text-xs focus:outline-none focus:border-cyan-400"
                    />
                  </div>
                </>
              )}
            </div>

            <div className="flex justify-between pt-4">
              <button
                onClick={() => setCurrentStep(2)}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-semibold transition-all"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>{t('back')}</span>
              </button>
              <button
                onClick={handleStartOnboard}
                disabled={flashing}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 active:scale-[0.99] text-white font-bold text-xs transition-all shadow-sm disabled:opacity-50"
              >
                <ShieldCheck className={`w-4 h-4 ${flashing ? 'animate-spin' : ''}`} />
                <span>{flashing ? t('flashing_in_progress') : t('start_flashing')}</span>
              </button>
            </div>
          </div>
        )}

        {currentStep === 4 && (
          <div className="space-y-4">
            <div className="p-4 rounded-2xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-300 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300 flex items-start gap-3">
              <CheckCircle2 className="w-6 h-6 text-emerald-600 dark:text-emerald-400 shrink-0" />
              <div>
                <h3 className="font-bold text-sm">{t('step4_success_title')}</h3>
                <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-1">{t('step4_success_desc')}</p>
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 font-mono text-xs space-y-2">
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
                className="px-6 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 active:scale-[0.99] text-white font-bold text-xs transition-all shadow-sm"
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
