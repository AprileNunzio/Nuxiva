import React, { useState, useEffect, useCallback } from 'react';
import {
  Monitor,
  Server,
  Clock,
  Calendar,
  Brain,
  MessageSquare,
  Mic,
  Activity,
  Eye,
  Sparkles,
  LayoutGrid,
  Volume2,
  Globe,
  Cpu,
  ShieldCheck,
  CheckCircle2,
  RefreshCw,
  ArrowLeft
} from 'lucide-react';
import { DisplaySettings, BackendSettings } from '../types';
import {
  fetchDisplaySettings,
  saveDisplaySettings,
  fetchBackendSettings,
  saveBackendSettings
} from '../api';

interface SystemSettingsViewProps {
  readonly t: (key: string, params?: Record<string, string | number>) => string;
  readonly lang: string;
  readonly onBack: () => void;
}

export const SystemSettingsView: React.FC<SystemSettingsViewProps> = ({ t, onBack }) => {
  const [display, setDisplay] = useState<DisplaySettings | null>(null);
  const [backend, setBackend] = useState<BackendSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [savingBackend, setSavingBackend] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const loadSettings = useCallback(async () => {
    setLoading(true);
    try {
      const [d, b] = await Promise.all([
        fetchDisplaySettings().catch(() => null),
        fetchBackendSettings().catch(() => null)
      ]);
      if (d) setDisplay(d);
      if (b) setBackend(b);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadSettings();
  }, [loadSettings]);

  const handleToggleDisplay = async (key: keyof DisplaySettings) => {
    if (!display) return;
    const nextVal = !display[key];
    const updated = { ...display, [key]: nextVal };
    setDisplay(updated);

    try {
      const bc = new BroadcastChannel('nuxiva_display_settings');
      bc.postMessage({ type: 'settings_updated', settings: updated });
      bc.close();
    } catch (_) {}

    try {
      localStorage.setItem('nuxiva_display_settings', JSON.stringify(updated));
    } catch (_) {}

    try {
      await saveDisplaySettings(updated);
      showToast(t('display_live_synced'));
    } catch (_) {
      showToast(t('sync_error'));
    }
  };

  const handleSessionModeChange = async (mode: 'shared' | 'isolated') => {
    if (!display) return;
    const updated: DisplaySettings = { ...display, session_mode: mode };
    setDisplay(updated);

    try {
      const bc = new BroadcastChannel('nuxiva_display_settings');
      bc.postMessage({ type: 'settings_updated', settings: updated });
      bc.close();
    } catch (_) {}

    try {
      localStorage.setItem('nuxiva_display_settings', JSON.stringify(updated));
    } catch (_) {}

    try {
      await saveDisplaySettings(updated);
      showToast(t('display_live_synced'));
    } catch (_) {
      showToast(t('sync_error'));
    }
  };

  const handleBackendFieldChange = <K extends keyof BackendSettings>(key: K, val: BackendSettings[K]) => {
    if (!backend) return;
    setBackend({ ...backend, [key]: val });
  };

  const handleSaveBackend = async () => {
    if (!backend) return;
    setSavingBackend(true);
    try {
      const res = await saveBackendSettings(backend);
      setBackend(res);
      showToast(t('backend_saved_success'));
    } catch (_) {
      showToast(t('sync_error'));
    } finally {
      setSavingBackend(false);
    }
  };

  if (loading && !display && !backend) {
    return (
      <div className="flex h-96 flex-col items-center justify-center gap-3">
        <RefreshCw className="h-8 w-8 animate-spin text-cyan-600" />
        <span className="text-sm font-medium text-slate-600">{t('loading')}</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-4 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-4">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onBack}
            className="flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-slate-300 hover:text-slate-950"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>{t('back_to_catalog')}</span>
          </button>
          <div>
            <h1 className="text-xl font-black tracking-wide text-cyan-700">{t('settings_title')}</h1>
            <p className="text-xs text-slate-600">{t('settings_subtitle')}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {toastMessage && (
            <div className="flex items-center gap-1.5 rounded-xl border border-emerald-300 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 shadow-lg shadow-emerald-500/10">
              <CheckCircle2 className="h-3.5 w-3.5" />
              <span>{toastMessage}</span>
            </div>
          )}
          <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
            </span>
            <span className="font-mono text-[11px] font-bold text-emerald-600">LIVE SYNC</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="flex flex-col rounded-2xl border border-cyan-300 bg-gradient-to-b from-white to-white p-5 shadow-xl shadow-cyan-950/20 backdrop-blur-md">
          <div className="mb-4 flex items-center justify-between border-b border-slate-200 pb-3">
            <div className="flex items-center gap-2.5">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-cyan-300 bg-cyan-50 text-cyan-700">
                <Monitor className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-sm font-bold tracking-wide text-slate-950">{t('card_frontend_title')}</h2>
                <p className="text-xs text-slate-600">{t('card_frontend_sub')}</p>
              </div>
            </div>
            <span className="rounded-full border border-cyan-300 bg-cyan-50 px-2.5 py-0.5 font-mono text-[10px] font-bold text-cyan-700">
              DISPLAY :80
            </span>
          </div>

          {display && (
            <div className="flex flex-col divide-y divide-slate-200 text-xs">
              <div className="py-2.5">
                <span className="mb-2 block font-mono text-[10px] uppercase tracking-wider text-slate-500">
                  {t('section_hud_elements')}
                </span>
                <div className="flex flex-col gap-2">
                  <SettingRow
                    icon={<Sparkles className="h-4 w-4 text-cyan-600" />}
                    title={t('opt_assistant_name')}
                    desc={t('opt_assistant_name_desc')}
                    active={display.show_assistant_name}
                    onToggle={() => void handleToggleDisplay('show_assistant_name')}
                  />
                  <SettingRow
                    icon={<Clock className="h-4 w-4 text-cyan-600" />}
                    title={t('opt_clock')}
                    desc={t('opt_clock_desc')}
                    active={display.show_clock}
                    onToggle={() => void handleToggleDisplay('show_clock')}
                  />
                  <SettingRow
                    icon={<Calendar className="h-4 w-4 text-cyan-600" />}
                    title={t('opt_date')}
                    desc={t('opt_date_desc')}
                    active={display.show_date}
                    onToggle={() => void handleToggleDisplay('show_date')}
                  />
                  <SettingRow
                    icon={<Brain className="h-4 w-4 text-cyan-600" />}
                    title={t('opt_thinking')}
                    desc={t('opt_thinking_desc')}
                    active={display.show_thinking}
                    onToggle={() => void handleToggleDisplay('show_thinking')}
                  />
                </div>
              </div>

              <div className="py-2.5">
                <span className="mb-2 block font-mono text-[10px] uppercase tracking-wider text-slate-500">
                  {t('section_dock_controls')}
                </span>
                <div className="flex flex-col gap-2">
                  <SettingRow
                    icon={<MessageSquare className="h-4 w-4 text-cyan-600" />}
                    title={t('opt_dock')}
                    desc={t('opt_dock_desc')}
                    active={display.show_dock}
                    onToggle={() => void handleToggleDisplay('show_dock')}
                  />
                  <SettingRow
                    icon={<Mic className="h-4 w-4 text-cyan-600" />}
                    title={t('opt_mic')}
                    desc={t('opt_mic_desc')}
                    active={display.show_mic}
                    onToggle={() => void handleToggleDisplay('show_mic')}
                  />
                </div>
              </div>

              <div className="py-2.5">
                <span className="mb-2 block font-mono text-[10px] uppercase tracking-wider text-slate-500">
                  {t('section_telemetry_graphics')}
                </span>
                <div className="flex flex-col gap-2">
                  <SettingRow
                    icon={<Activity className="h-4 w-4 text-cyan-600" />}
                    title={t('opt_telemetry_chips')}
                    desc={t('opt_telemetry_chips_desc')}
                    active={display.show_telemetry_chips}
                    onToggle={() => void handleToggleDisplay('show_telemetry_chips')}
                  />
                  <SettingRow
                    icon={<Eye className="h-4 w-4 text-cyan-600" />}
                    title={t('opt_presence')}
                    desc={t('opt_presence_desc')}
                    active={display.show_presence}
                    onToggle={() => void handleToggleDisplay('show_presence')}
                  />
                  <SettingRow
                    icon={<Cpu className="h-4 w-4 text-cyan-600" />}
                    title={t('opt_holo_avatar')}
                    desc={t('opt_holo_avatar_desc')}
                    active={display.show_holo_avatar}
                    onToggle={() => void handleToggleDisplay('show_holo_avatar')}
                  />
                  <SettingRow
                    icon={<LayoutGrid className="h-4 w-4 text-cyan-600" />}
                    title={t('opt_desk_widgets')}
                    desc={t('opt_desk_widgets_desc')}
                    active={display.show_desk_widgets}
                    onToggle={() => void handleToggleDisplay('show_desk_widgets')}
                  />
                  <SettingRow
                    icon={<Volume2 className="h-4 w-4 text-cyan-600" />}
                    title={t('opt_sound_effects')}
                    desc={t('opt_sound_effects_desc')}
                    active={display.sound_effects}
                    onToggle={() => void handleToggleDisplay('sound_effects')}
                  />
                </div>
              </div>

              <div className="py-2.5">
                <span className="mb-2 block font-mono text-[10px] uppercase tracking-wider text-slate-500">
                  {t('section_display_session')}
                </span>
                <div className="flex flex-col gap-2 rounded-xl border border-slate-200 bg-white p-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <Globe className="h-4 w-4 text-cyan-600" />
                      <span className="font-semibold text-slate-950">{t('opt_session_mode')}</span>
                    </div>
                    <span className="font-mono text-[10px] font-bold uppercase text-cyan-700">
                      {display.session_mode === 'isolated' ? t('mode_isolated_badge') : t('mode_shared_badge')}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-600">{t('opt_session_mode_desc')}</p>
                  <div className="mt-1 grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => void handleSessionModeChange('shared')}
                      className={`flex flex-col rounded-lg border p-2 text-left transition ${
                        (display.session_mode || 'shared') === 'shared'
                          ? 'border-cyan-500 bg-cyan-50/70 text-cyan-950 shadow-sm'
                          : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'
                      }`}
                    >
                      <span className="text-xs font-bold">{t('opt_session_shared')}</span>
                      <span className="text-[10px] text-slate-500">{t('opt_session_shared_desc')}</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleSessionModeChange('isolated')}
                      className={`flex flex-col rounded-lg border p-2 text-left transition ${
                        display.session_mode === 'isolated'
                          ? 'border-cyan-500 bg-cyan-50/70 text-cyan-950 shadow-sm'
                          : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'
                      }`}
                    >
                      <span className="text-xs font-bold">{t('opt_session_isolated')}</span>
                      <span className="text-[10px] text-slate-500">{t('opt_session_isolated_desc')}</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="flex flex-col rounded-2xl border border-emerald-300 bg-gradient-to-b from-white to-white p-5 shadow-xl shadow-emerald-950/20 backdrop-blur-md">
          <div className="mb-4 flex items-center justify-between border-b border-slate-200 pb-3">
            <div className="flex items-center gap-2.5">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-emerald-300 bg-emerald-50 text-emerald-700">
                <Server className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-sm font-bold tracking-wide text-slate-950">{t('card_backend_title')}</h2>
                <p className="text-xs text-slate-600">{t('card_backend_sub')}</p>
              </div>
            </div>
            <span className="rounded-full border border-emerald-300 bg-emerald-50 px-2.5 py-0.5 font-mono text-[10px] font-bold text-emerald-700">
              MESH & LLM
            </span>
          </div>

          {backend && (
            <div className="flex flex-col gap-4 text-xs">
              <div className="flex flex-col gap-2">
                <SettingRow
                  icon={<ShieldCheck className="h-4 w-4 text-emerald-600" />}
                  title={t('opt_auto_shutdown_local')}
                  desc={t('opt_auto_shutdown_local_desc')}
                  active={backend.auto_shutdown_local_ollama}
                  onToggle={() => handleBackendFieldChange('auto_shutdown_local_ollama', !backend.auto_shutdown_local_ollama)}
                />
                <SettingRow
                  icon={<Globe className="h-4 w-4 text-emerald-600" />}
                  title={t('opt_mesh_broadcast')}
                  desc={t('opt_mesh_broadcast_desc')}
                  active={backend.mesh_broadcast}
                  onToggle={() => handleBackendFieldChange('mesh_broadcast', !backend.mesh_broadcast)}
                />
                <SettingRow
                  icon={<RefreshCw className="h-4 w-4 text-emerald-600" />}
                  title={t('opt_mesh_state_sync')}
                  desc={t('opt_mesh_state_sync_desc')}
                  active={backend.mesh_state_sync}
                  onToggle={() => handleBackendFieldChange('mesh_state_sync', !backend.mesh_state_sync)}
                />
                <SettingRow
                  icon={<ShieldCheck className="h-4 w-4 text-emerald-600" />}
                  title={t('opt_process_watchdog')}
                  desc={t('opt_process_watchdog_desc')}
                  active={backend.process_watchdog}
                  onToggle={() => handleBackendFieldChange('process_watchdog', !backend.process_watchdog)}
                />
                <SettingRow
                  icon={<Activity className="h-4 w-4 text-emerald-600" />}
                  title={t('opt_verbose_telemetry')}
                  desc={t('opt_verbose_telemetry_desc')}
                  active={backend.verbose_telemetry}
                  onToggle={() => handleBackendFieldChange('verbose_telemetry', !backend.verbose_telemetry)}
                />
              </div>

              <div className="mt-2 flex justify-end">
                <button
                  type="button"
                  onClick={() => void handleSaveBackend()}
                  disabled={savingBackend}
                  className="flex items-center gap-2 rounded-xl border border-emerald-300 bg-gradient-to-r from-emerald-600 to-teal-600 px-5 py-2 font-bold text-white shadow-lg shadow-emerald-900/30 transition hover:brightness-110 disabled:opacity-50"
                >
                  {savingBackend ? <RefreshCw className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
                  <span>{savingBackend ? t('saving') : t('btn_save_backend')}</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

interface SettingRowProps {
  readonly icon: React.ReactNode;
  readonly title: string;
  readonly desc: string;
  readonly active: boolean;
  readonly onToggle: () => void;
}

const SettingRow: React.FC<SettingRowProps> = ({ icon, title, desc, active, onToggle }) => (
  <div className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-2.5 transition hover:border-slate-300">
    <div className="flex items-start gap-2.5">
      <div className="mt-0.5">{icon}</div>
      <div>
        <div className="font-semibold text-slate-950">{title}</div>
        <div className="text-[11px] text-slate-600">{desc}</div>
      </div>
    </div>
    <button
      type="button"
      onClick={onToggle}
      className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
        active ? 'bg-cyan-500 shadow-md shadow-cyan-500/30' : 'bg-slate-100'
      }`}
    >
      <span
        className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-lg ring-0 transition duration-200 ease-in-out ${
          active ? 'translate-x-5' : 'translate-x-0'
        }`}
      />
    </button>
  </div>
);
