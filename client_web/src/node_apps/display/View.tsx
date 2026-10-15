import React, { useState, useEffect } from 'react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import {
  Monitor,
  Maximize2,
  Minimize2,
  Sun,
  Moon,
  Clock,
  Sparkles,
  Save,
  CheckCircle2,
  RefreshCw,
  Compass,
} from 'lucide-react';

interface Props {
  nodeId?: string;
}

export const View: React.FC<Props> = ({ nodeId = 'node-01' }) => {
  const { t } = useScopedI18n('node_apps/display');

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  // Avatar Style
  const [avatarStyle, setAvatarStyle] = useState<'holo' | 'orb' | 'wave' | 'matrix'>('holo');

  // Display Settings
  const [kioskActive, setKioskActive] = useState(false);
  const [orientation, setOrientation] = useState<'landscape' | 'portrait' | 'inverted'>('landscape');
  const [brightness, setBrightness] = useState(85);
  const [sleepTimer, setSleepTimer] = useState('5m');
  const [showAmbient, setShowAmbient] = useState(true);

  useEffect(() => {
    let isMounted = true;
    const fetchHardware = async () => {
      try {
        setLoading(true);
        const res = await fetch(`/api/v5/nodes/${nodeId}/hardware`);
        if (res.ok) {
          const data = await res.json();
          if (isMounted && data.display) {
            setKioskActive(!!data.display.kiosk_active);
            if (data.display.orientation) setOrientation(data.display.orientation);
            if (typeof data.display.brightness === 'number') setBrightness(data.display.brightness);
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

  const handleToggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
      setKioskActive(true);
    } else {
      document.exitFullscreen().catch(() => {});
      setKioskActive(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await fetch(`/api/v5/nodes/${nodeId}/apps/display/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          enabled: true,
          settings: {
            avatarStyle,
            kioskActive,
            orientation,
            brightness,
            sleepTimer,
            showAmbient,
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

  if (loading) {
    return (
      <div className="p-12 flex flex-col items-center justify-center text-slate-400 font-mono gap-3">
        <RefreshCw className="w-6 h-6 animate-spin text-cyan-400" />
        <span className="text-xs">Rilevamento display e interfaccia grafica...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6 font-mono text-slate-100">
      {/* Header */}
      <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-xl">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
            <Monitor className="w-5 h-5" />
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

      {/* Avatar Style Picker & Live Visual Canvas */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-4">
        <div>
          <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-cyan-400" />
            {t('avatar_title')}
          </div>
          <p className="text-xs text-slate-400 mt-0.5">{t('avatar_desc')}</p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {(['holo', 'orb', 'wave', 'matrix'] as const).map((styleKey) => {
            const isSelected = avatarStyle === styleKey;
            return (
              <div
                key={styleKey}
                onClick={() => setAvatarStyle(styleKey)}
                className={`p-3.5 rounded-xl border cursor-pointer transition text-center ${
                  isSelected
                    ? 'bg-cyan-950/30 border-cyan-500/60 ring-1 ring-cyan-500/50 shadow-[0_0_15px_rgba(6,182,212,0.2)]'
                    : 'bg-slate-950 border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="text-xs font-bold text-white mb-1">{t(`avatar_${styleKey}`)}</div>
                <span className={`text-[10px] font-semibold ${isSelected ? 'text-cyan-400' : 'text-slate-500'}`}>
                  {isSelected ? 'SELEZIONATO' : 'ATTIVA'}
                </span>
              </div>
            );
          })}
        </div>

        {/* Live Animated Avatar Face Viewport */}
        <div className="mt-4 relative h-64 bg-[#030712] border border-cyan-950/80 rounded-2xl flex items-center justify-center overflow-hidden shadow-2xl">
          <div className="absolute top-3 left-4 text-[10px] text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
            <Sparkles className="w-3 h-3 text-cyan-400" />
            {t('avatar_preview')}
          </div>

          {/* Style 1: 3D Holographic Core */}
          {avatarStyle === 'holo' && (
            <div className="relative w-44 h-44 flex items-center justify-center">
              <div className="absolute inset-0 rounded-full border-2 border-dashed border-cyan-500/40 animate-[spin_10s_linear_infinite]" />
              <div className="absolute inset-4 rounded-full border border-cyan-400/60 animate-[spin_6s_linear_infinite_reverse]" />
              <div className="absolute inset-8 rounded-full border border-purple-500/50 animate-[spin_8s_linear_infinite]" />
              <div className="w-16 h-16 rounded-full bg-cyan-400/20 backdrop-blur-md border border-cyan-300 shadow-[0_0_35px_#06b6d4] flex items-center justify-center">
                <div className="w-6 h-6 rounded-full bg-cyan-300 shadow-[0_0_15px_#ffffff] animate-ping" />
              </div>
            </div>
          )}

          {/* Style 2: Cyber-Orb */}
          {avatarStyle === 'orb' && (
            <div className="relative w-40 h-40 flex items-center justify-center">
              <div className="absolute inset-0 rounded-full bg-gradient-to-tr from-cyan-500 via-purple-600 to-emerald-400 opacity-60 blur-xl animate-pulse" />
              <div className="relative w-28 h-28 rounded-full bg-radial from-cyan-300 via-cyan-600 to-slate-950 border border-cyan-300/60 shadow-[0_0_50px_rgba(6,182,212,0.8)] flex items-center justify-center">
                <div className="w-12 h-12 rounded-full border-2 border-white/40 animate-ping" />
              </div>
            </div>
          )}

          {/* Style 3: Quantum Waveform */}
          {avatarStyle === 'wave' && (
            <div className="w-full px-12 flex items-center justify-center gap-1.5 h-32">
              {Array.from({ length: 24 }).map((_, i) => (
                <div
                  key={i}
                  style={{
                    height: `${Math.sin(i * 0.3) * 45 + 50}%`,
                    animation: `pulse 1.2s ease-in-out infinite alternate ${i * 0.05}s`,
                  }}
                  className="w-1.5 rounded-full bg-gradient-to-t from-cyan-600 via-cyan-400 to-white shadow-[0_0_10px_#06b6d4]"
                />
              ))}
            </div>
          )}

          {/* Style 4: Particle Matrix */}
          {avatarStyle === 'matrix' && (
            <div className="grid grid-cols-7 gap-3">
              {Array.from({ length: 28 }).map((_, i) => (
                <div
                  key={i}
                  style={{ animationDelay: `${(i % 5) * 0.2}s` }}
                  className="w-2.5 h-2.5 rounded-sm bg-emerald-400 shadow-[0_0_8px_#10b981] animate-pulse"
                />
              ))}
            </div>
          )}

          {/* Ambient Overlay preview if enabled */}
          {showAmbient && (
            <div className="absolute bottom-3 right-4 text-[10px] text-slate-400 flex items-center gap-3 bg-slate-900/80 px-3 py-1.5 rounded-lg border border-slate-800">
              <span className="flex items-center gap-1 text-white">
                <Clock className="w-3 h-3 text-cyan-400" /> 12:00
              </span>
              <span>21 °C Sereno</span>
            </div>
          )}
        </div>
      </div>

      {/* Kiosk Mode & Orientation Controls */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Kiosk Fullscreen Switch */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                <Maximize2 className="w-4 h-4 text-cyan-400" />
                {t('kiosk_title')}
              </div>
              <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold border ${
                kioskActive ? 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30' : 'bg-slate-800 text-slate-500'
              }`}>
                {kioskActive ? t('kiosk_active') : t('kiosk_inactive')}
              </span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">{t('kiosk_desc')}</p>
          </div>

          <button
            onClick={handleToggleFullscreen}
            className={`w-full py-2.5 rounded-xl text-xs font-bold transition flex items-center justify-center gap-2 cursor-pointer ${
              kioskActive
                ? 'bg-rose-600 hover:bg-rose-500 text-white shadow-lg shadow-rose-600/20'
                : 'bg-cyan-600 hover:bg-cyan-500 text-white shadow-lg shadow-cyan-600/20'
            }`}
          >
            {kioskActive ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
            {kioskActive ? 'ESCI DALLA MODALITÀ KIOSK' : 'ATTIVA KIOSK A SCHERMO INTERO'}
          </button>
        </div>

        {/* Orientation & Sleep */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-4">
          <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
            <Compass className="w-4 h-4 text-cyan-400" />
            {t('orientation')}
          </div>

          <div className="grid grid-cols-3 gap-2">
            {(['landscape', 'portrait', 'inverted'] as const).map((orient) => (
              <button
                key={orient}
                onClick={() => setOrientation(orient)}
                className={`px-3 py-2 rounded-xl text-xs font-semibold border transition ${
                  orientation === orient
                    ? 'bg-cyan-500/15 border-cyan-500/50 text-cyan-300'
                    : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                }`}
              >
                {t(`orient_${orient}`)}
              </button>
            ))}
          </div>

          <div className="pt-3 border-t border-slate-800">
            <div className="flex justify-between items-center text-xs text-slate-300 mb-1.5">
              <span className="flex items-center gap-1.5">
                <Sun className="w-3.5 h-3.5 text-amber-400" />
                {t('brightness')}
              </span>
              <span className="font-bold text-amber-400">{brightness}%</span>
            </div>
            <input
              type="range"
              min="10"
              max="100"
              value={brightness}
              onChange={(e) => setBrightness(parseInt(e.target.value, 10))}
              className="w-full accent-amber-500 bg-slate-950 rounded-lg h-2 cursor-pointer"
            />
          </div>

          <div className="flex items-center justify-between pt-2">
            <span className="text-xs text-slate-400 flex items-center gap-1.5">
              <Moon className="w-3.5 h-3.5 text-purple-400" />
              {t('sleep_timer')}
            </span>
            <select
              value={sleepTimer}
              onChange={(e) => setSleepTimer(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1 text-xs text-white"
            >
              <option value="never">{t('sleep_never')}</option>
              <option value="1m">{t('sleep_1m')}</option>
              <option value="5m">{t('sleep_5m')}</option>
              <option value="15m">{t('sleep_15m')}</option>
            </select>
          </div>

          <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between">
            <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={showAmbient}
                onChange={(e) => setShowAmbient(e.target.checked)}
                className="accent-cyan-500 rounded"
              />
              <span>{t('show_ambient')}</span>
            </label>
          </div>
        </div>
      </div>
    </div>
  );
};

export default View;
