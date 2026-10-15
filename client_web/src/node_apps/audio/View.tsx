import React, { useState, useEffect, useRef } from 'react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import {
  Volume2,
  VolumeX,
  Play,
  Save,
  CheckCircle2,
  Sliders,
  Radio,
  Activity,
  Layers,
  Sparkles,
  RefreshCw,
} from 'lucide-react';

interface Props {
  nodeId?: string;
}

interface AudioDevice {
  id: string;
  name: string;
  type: string;
  channels: number;
  sample_rate: number;
}

export const View: React.FC<Props> = ({ nodeId = 'node-01' }) => {
  const { t } = useScopedI18n('node_apps/audio');

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  // Audio parameters
  const [devices, setDevices] = useState<AudioDevice[]>([]);
  const [selectedDevice, setSelectedDevice] = useState('');
  const [volume, setVolume] = useState(75);
  const [isMuted, setIsMuted] = useState(false);
  const [profile, setProfile] = useState<'voice' | 'music' | 'night' | 'chime'>('voice');

  // EQ
  const [bass, setBass] = useState(0);
  const [mid, setMid] = useState(2);
  const [treble, setTreble] = useState(1);

  // Tone generator test
  const [testFreq, setTestFreq] = useState(440);
  const [isPlaying, setIsPlaying] = useState(false);
  const audioCtxRef = useRef<AudioContext | null>(null);

  const fetchHardware = async (isMounted = true) => {
    try {
      setLoading(true);
      const res = await fetch(`/api/v5/nodes/${nodeId}/hardware`);
      if (res.ok) {
        const data = await res.json();
        if (isMounted) {
          if (Array.isArray(data.audio_outputs) && data.audio_outputs.length > 0) {
            setDevices(data.audio_outputs);
            setSelectedDevice(data.audio_outputs[0].id);
          } else {
            setDevices([]);
            setSelectedDevice('');
          }
        }
      }
    } catch (err) {
      console.warn('Hardware fetch failed', err);
    } finally {
      if (isMounted) setLoading(false);
    }
  };

  useEffect(() => {
    let isMounted = true;
    fetchHardware(isMounted);
    return () => {
      isMounted = false;
      if (audioCtxRef.current) {
        audioCtxRef.current.close().catch(() => {});
      }
    };
  }, [nodeId]);

  const handlePlayTone = async () => {
    if (isPlaying) return;
    setIsPlaying(true);

    try {
      // 1. Play synthesized tone in browser via Web Audio API
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (AudioCtx) {
        const ctx = new AudioCtx();
        audioCtxRef.current = ctx;
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        osc.type = 'sine';
        osc.frequency.setValueAtTime(testFreq, ctx.currentTime);

        const currentVol = isMuted ? 0 : volume / 100;
        gain.gain.setValueAtTime(0.01, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(Math.max(0.01, currentVol * 0.4), ctx.currentTime + 0.05);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 1.2);

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start();
        osc.stop(ctx.currentTime + 1.25);
      }

      // 2. Notify node backend
      await fetch(`/api/v5/nodes/${nodeId}/hardware/test_audio`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          output_device: selectedDevice,
          frequency: testFreq,
          duration_ms: 1200,
        }),
      });
    } catch (err) {
      console.warn('Audio tone error', err);
    } finally {
      setTimeout(() => setIsPlaying(false), 1300);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await fetch(`/api/v5/nodes/${nodeId}/apps/audio/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          enabled: true,
          settings: {
            selectedDevice,
            volume,
            isMuted,
            profile,
            bass,
            mid,
            treble,
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
        <span className="text-xs">Rilevamento interfaccia audio nodo...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6 font-mono text-slate-100">
      {/* Header */}
      <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-xl">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
            <Volume2 className="w-5 h-5" />
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

      {/* Device & Master Volume Cockpit */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Output Device */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-4">
          <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
            <Radio className="w-4 h-4 text-cyan-400" />
            {t('output_device')}
          </div>

          <div className="space-y-2">
            {devices.length === 0 ? (
              <div className="text-xs text-slate-500 text-center py-6 bg-slate-950/40 rounded-xl border border-slate-800/80">
                Nessun dispositivo di output audio rilevato sul nodo.
              </div>
            ) : (
              devices.map((dev) => (
                <div
                  key={dev.id}
                  onClick={() => setSelectedDevice(dev.id)}
                  className={`p-3.5 rounded-xl border cursor-pointer transition flex items-center justify-between ${
                    selectedDevice === dev.id
                      ? 'bg-cyan-950/30 border-cyan-500/60 ring-1 ring-cyan-500/40'
                      : 'bg-slate-950/70 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div>
                    <div className="text-xs font-bold text-white">{dev.name}</div>
                    <div className="text-[10px] text-slate-500 mt-0.5">
                      ID: {dev.id} · {dev.channels} Canali · {dev.sample_rate / 1000} kHz
                    </div>
                  </div>
                  {selectedDevice === dev.id && <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 shadow-[0_0_8px_#06b6d4]" />}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Master Volume */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 flex flex-col justify-between space-y-4">
          <div>
            <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center justify-between mb-4">
              <span className="flex items-center gap-2">
                <Sliders className="w-4 h-4 text-cyan-400" />
                {t('master_volume')}
              </span>
              <button
                onClick={() => setIsMuted(!isMuted)}
                className={`px-2.5 py-1 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition ${
                  isMuted ? 'bg-rose-500/20 text-rose-400 border border-rose-500/40' : 'bg-slate-800 text-slate-300 hover:text-white'
                }`}
              >
                {isMuted ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
                {isMuted ? t('mute') : 'ATTIVO'}
              </button>
            </div>

            <div className="space-y-3">
              <div className="flex justify-between items-end">
                <span className="text-3xl font-extrabold text-white">
                  {isMuted ? '0%' : `${volume}%`}
                </span>
                <span className="text-xs text-slate-400">
                  {isMuted ? '-∞ dB' : `${Math.round((volume - 100) * 0.4)} dB`}
                </span>
              </div>

              <input
                type="range"
                min="0"
                max="100"
                value={isMuted ? 0 : volume}
                disabled={isMuted}
                onChange={(e) => setVolume(parseInt(e.target.value, 10))}
                className="w-full accent-cyan-500 bg-slate-950 rounded-lg h-2.5 cursor-pointer disabled:opacity-40"
              />
            </div>
          </div>

          {/* Equalizer Presets */}
          <div className="pt-4 border-t border-slate-800/80">
            <div className="text-[11px] text-slate-400 mb-2 flex items-center gap-1">
              <Sparkles className="w-3 h-3 text-cyan-400" />
              {t('profile_title')}
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              {(['voice', 'music', 'night', 'chime'] as const).map((pKey) => (
                <button
                  key={pKey}
                  onClick={() => setProfile(pKey)}
                  className={`px-3 py-2 rounded-lg text-[11px] font-medium border text-left transition ${
                    profile === pKey
                      ? 'bg-cyan-500/15 border-cyan-500/50 text-cyan-300'
                      : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                  }`}
                >
                  {t(`profile_${pKey}`)}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* 3-Band Equalizer Sliders */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-4">
        <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
          <Layers className="w-4 h-4 text-cyan-400" />
          Equalizzatore a 3 Bande Hardware
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-2">
          <div>
            <div className="flex justify-between text-xs text-slate-300 mb-1.5">
              <span>{t('eq_bass')}</span>
              <span className="font-bold text-cyan-400">{bass > 0 ? `+${bass}` : bass} dB</span>
            </div>
            <input
              type="range"
              min="-12"
              max="12"
              value={bass}
              onChange={(e) => setBass(parseInt(e.target.value, 10))}
              className="w-full accent-cyan-500 bg-slate-950 rounded-lg h-1.5 cursor-pointer"
            />
          </div>

          <div>
            <div className="flex justify-between text-xs text-slate-300 mb-1.5">
              <span>{t('eq_mid')}</span>
              <span className="font-bold text-cyan-400">{mid > 0 ? `+${mid}` : mid} dB</span>
            </div>
            <input
              type="range"
              min="-12"
              max="12"
              value={mid}
              onChange={(e) => setMid(parseInt(e.target.value, 10))}
              className="w-full accent-cyan-500 bg-slate-950 rounded-lg h-1.5 cursor-pointer"
            />
          </div>

          <div>
            <div className="flex justify-between text-xs text-slate-300 mb-1.5">
              <span>{t('eq_treble')}</span>
              <span className="font-bold text-cyan-400">{treble > 0 ? `+${treble}` : treble} dB</span>
            </div>
            <input
              type="range"
              min="-12"
              max="12"
              value={treble}
              onChange={(e) => setTreble(parseInt(e.target.value, 10))}
              className="w-full accent-cyan-500 bg-slate-950 rounded-lg h-1.5 cursor-pointer"
            />
          </div>
        </div>
      </div>

      {/* Diagnostic Tone Test & Spectrum Visualizer */}
      <div className="bg-slate-950 border border-slate-800 rounded-2xl p-6 space-y-4">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div>
            <div className="text-xs font-semibold text-cyan-400 flex items-center gap-2">
              <Activity className="w-4 h-4" />
              {t('test_tone_title')}
            </div>
            <p className="text-xs text-slate-400 mt-0.5">{t('test_tone_desc')}</p>
          </div>

          <div className="flex items-center gap-3">
            <select
              value={testFreq}
              onChange={(e) => setTestFreq(parseInt(e.target.value, 10))}
              className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
            >
              <option value="440">440 Hz (La Standard / Pitch A4)</option>
              <option value="880">880 Hz (La5 / Ottava Superiore)</option>
              <option value="1000">1000 Hz (Tono di Allarme 1 kHz)</option>
            </select>

            <button
              onClick={handlePlayTone}
              disabled={isPlaying}
              className="flex items-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-xs font-bold transition shadow-lg shadow-cyan-600/20 disabled:opacity-50 cursor-pointer"
            >
              {isPlaying ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
              {isPlaying ? t('playing') : t('test_btn')}
            </button>
          </div>
        </div>

        {/* Real-time Simulated Spectrum Visualizer */}
        <div className="space-y-2">
          <div className="text-[11px] text-slate-500 flex justify-between">
            <span>{t('spectrum_title')}</span>
            <span>20 Hz — 20 kHz</span>
          </div>
          <div className="h-16 bg-slate-900/80 rounded-xl p-3 flex items-end justify-between gap-1 border border-slate-800/80">
            {Array.from({ length: 32 }).map((_, i) => {
              const activeHeight = isPlaying
                ? Math.sin(i * 0.4 + Date.now() * 0.01) * 35 + 40
                : (Math.sin(i * 0.3) * 10 + 15) * (volume / 100);
              return (
                <div
                  key={i}
                  style={{ height: `${Math.max(8, Math.min(100, activeHeight))}%` }}
                  className={`w-full rounded-t transition-all duration-100 ${
                    isPlaying
                      ? 'bg-gradient-to-t from-cyan-600 to-emerald-400'
                      : 'bg-gradient-to-t from-slate-800 to-cyan-900'
                  }`}
                />
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};

export default View;
