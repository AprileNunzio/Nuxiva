import React, { useState, useEffect, useRef } from 'react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import {
  Mic,
  Sliders,
  Shield,
  Activity,
  Save,
  CheckCircle2,
  Play,
  Square,
  Sparkles,
  Zap,
  RefreshCw,
  Cpu,
} from 'lucide-react';

interface Props {
  nodeId?: string;
}

interface AudioInputDevice {
  id: string;
  name: string;
  type: string;
  channels: number;
  vad_supported: boolean;
}

export const View: React.FC<Props> = ({ nodeId = 'node-01' }) => {
  const { t } = useScopedI18n('node_apps/mic');

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  // Input devices
  const [devices, setDevices] = useState<AudioInputDevice[]>([]);
  const [selectedDevice, setSelectedDevice] = useState('');

  // Controls
  const [gain, setGain] = useState(80);
  const [vadThreshold, setVadThreshold] = useState(35);
  const [rnnoise, setRnnoise] = useState(true);
  const [aec, setAec] = useState(true);
  const [agc, setAgc] = useState(true);
  const [wakeWord, setWakeWord] = useState('Ehi Nuxiva');

  // VU Meter & Live Test
  const [vuLevel, setVuLevel] = useState(0);
  const [isRecording, setIsRecording] = useState(false);
  const [recordSecondsLeft, setRecordSecondsLeft] = useState(0);
  const [recordedAudioUrl, setRecordedAudioUrl] = useState<string | null>(null);
  const [isPlayingRecorded, setIsPlayingRecorded] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const fetchHardware = async (isMounted = true) => {
    try {
      setLoading(true);
      const res = await fetch(`/api/v5/nodes/${nodeId}/hardware`);
      if (res.ok) {
        const data = await res.json();
        if (isMounted) {
          if (Array.isArray(data.audio_inputs) && data.audio_inputs.length > 0) {
            setDevices(data.audio_inputs);
            setSelectedDevice(data.audio_inputs[0].id);
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
    };
  }, [nodeId]);

  const handleStartTestRecord = async () => {
    if (isRecording) return;
    setIsRecording(true);
    setRecordSecondsLeft(5);
    setRecordedAudioUrl(null);
    audioChunksRef.current = [];

    // Attempt browser mic recording with real Web Audio analyser
    try {
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mediaRecorder = new MediaRecorder(stream);
        mediaRecorderRef.current = mediaRecorder;

        const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
        if (AudioCtx) {
          const audioCtx = new AudioCtx();
          const source = audioCtx.createMediaStreamSource(stream);
          const analyser = audioCtx.createAnalyser();
          analyser.fftSize = 128;
          source.connect(analyser);
          const dataArray = new Uint8Array(analyser.frequencyBinCount);

          const updateVu = () => {
            if (!mediaRecorderRef.current || mediaRecorderRef.current.state !== 'recording') {
              setVuLevel(0);
              audioCtx.close().catch(() => {});
              return;
            }
            analyser.getByteFrequencyData(dataArray);
            let sum = 0;
            for (let i = 0; i < dataArray.length; i++) sum += dataArray[i];
            const avg = sum / dataArray.length;
            setVuLevel(Math.min(100, Math.round((avg / 128) * 100)));
            requestAnimationFrame(updateVu);
          };
          requestAnimationFrame(updateVu);
        }

        mediaRecorder.ondataavailable = (e) => {
          if (e.data.size > 0) audioChunksRef.current.push(e.data);
        };

        mediaRecorder.onstop = () => {
          const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
          const url = URL.createObjectURL(audioBlob);
          setRecordedAudioUrl(url);
          setVuLevel(0);
          stream.getTracks().forEach((track) => track.stop());
        };

        mediaRecorder.start();
      }
    } catch {
      // Browser mic permission denied or not supported
    }

    const timer = setInterval(() => {
      setRecordSecondsLeft((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          setIsRecording(false);
          setVuLevel(0);
          if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
            mediaRecorderRef.current.stop();
          }
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const handlePlayRecording = () => {
    if (recordedAudioUrl) {
      const audio = new Audio(recordedAudioUrl);
      setIsPlayingRecorded(true);
      audio.onended = () => setIsPlayingRecorded(false);
      audio.play().catch(() => setIsPlayingRecorded(false));
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await fetch(`/api/v5/nodes/${nodeId}/apps/mic/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          enabled: true,
          settings: {
            selectedDevice,
            gain,
            vadThreshold,
            rnnoise,
            aec,
            agc,
            wakeWord,
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
        <span className="text-xs">Rilevamento microfoni del nodo...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6 font-mono text-slate-100">
      {/* Header */}
      <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-xl">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
            <Mic className="w-5 h-5" />
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

      {/* Primary Input & Gain Cockpit */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Device Selection */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-4">
          <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
            <Mic className="w-4 h-4 text-cyan-400" />
            {t('input_device')}
          </div>

          <div className="space-y-2">
            {devices.length === 0 ? (
              <div className="text-xs text-slate-500 text-center py-6 bg-slate-950/40 rounded-xl border border-slate-800/80">
                Nessun microfono rilevato sul nodo.
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
                      Port: {dev.id} · {dev.channels} Canali · {dev.vad_supported ? 'VAD Hardware Supportato' : 'VAD Software'}
                    </div>
                  </div>
                  {selectedDevice === dev.id && <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 shadow-[0_0_8px_#06b6d4]" />}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Gain & VAD Sliders */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 flex flex-col justify-between space-y-6">
          <div>
            <div className="flex justify-between items-center text-xs text-slate-300 mb-2">
              <span className="font-semibold flex items-center gap-1.5">
                <Sliders className="w-4 h-4 text-cyan-400" />
                {t('input_gain')}
              </span>
              <span className="font-bold text-cyan-400">{gain}% (+{Math.round(gain * 0.2)} dB)</span>
            </div>
            <input
              type="range"
              min="10"
              max="150"
              value={gain}
              onChange={(e) => setGain(parseInt(e.target.value, 10))}
              className="w-full accent-cyan-500 bg-slate-950 rounded-lg h-2 cursor-pointer"
            />
          </div>

          <div>
            <div className="flex justify-between items-center text-xs text-slate-300 mb-2">
              <span className="font-semibold flex items-center gap-1.5">
                <Activity className="w-4 h-4 text-purple-400" />
                {t('vad_threshold')}
              </span>
              <span className="font-bold text-purple-400">{vadThreshold}%</span>
            </div>
            <input
              type="range"
              min="5"
              max="90"
              value={vadThreshold}
              onChange={(e) => setVadThreshold(parseInt(e.target.value, 10))}
              className="w-full accent-purple-500 bg-slate-950 rounded-lg h-2 cursor-pointer"
            />
            <p className="text-[10px] text-slate-500 mt-1">{t('vad_desc')}</p>
          </div>

          <div className="pt-3 border-t border-slate-800 flex items-center justify-between text-xs">
            <span className="text-slate-400 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              {t('wakeword_title')}
            </span>
            <select
              value={wakeWord}
              onChange={(e) => setWakeWord(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1 text-xs text-cyan-300 font-semibold"
            >
              <option value="Ehi Nuxiva">Ehi Nuxiva</option>
              <option value="Nuxiva">Nuxiva</option>
              <option value="Computer">Computer</option>
              <option value="Jarvis">Jarvis</option>
            </select>
          </div>
        </div>
      </div>

      {/* DSP Filters */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-4">
        <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
          <Shield className="w-4 h-4 text-cyan-400" />
          {t('dsp_title')}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div
            onClick={() => setRnnoise(!rnnoise)}
            className={`p-4 rounded-xl border cursor-pointer transition ${
              rnnoise ? 'bg-cyan-950/20 border-cyan-500/50' : 'bg-slate-950 border-slate-800'
            }`}
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-bold text-white flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5 text-cyan-400" />
                {t('rnnoise_toggle')}
              </span>
              <span className={`text-[10px] font-bold ${rnnoise ? 'text-cyan-400' : 'text-slate-500'}`}>
                {rnnoise ? 'ON' : 'OFF'}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">{t('rnnoise_desc')}</p>
          </div>

          <div
            onClick={() => setAec(!aec)}
            className={`p-4 rounded-xl border cursor-pointer transition ${
              aec ? 'bg-purple-950/20 border-purple-500/50' : 'bg-slate-950 border-slate-800'
            }`}
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-bold text-white flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-purple-400" />
                {t('aec_toggle')}
              </span>
              <span className={`text-[10px] font-bold ${aec ? 'text-purple-400' : 'text-slate-500'}`}>
                {aec ? 'ON' : 'OFF'}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">{t('aec_desc')}</p>
          </div>

          <div
            onClick={() => setAgc(!agc)}
            className={`p-4 rounded-xl border cursor-pointer transition ${
              agc ? 'bg-emerald-950/20 border-emerald-500/50' : 'bg-slate-950 border-slate-800'
            }`}
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-bold text-white flex items-center gap-1.5">
                <Activity className="w-3.5 h-3.5 text-emerald-400" />
                {t('agc_toggle')}
              </span>
              <span className={`text-[10px] font-bold ${agc ? 'text-emerald-400' : 'text-slate-500'}`}>
                {agc ? 'ON' : 'OFF'}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">{t('agc_desc')}</p>
          </div>
        </div>
      </div>

      {/* Real-Time VU-Meter & 5s Live Test */}
      <div className="bg-slate-950 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div>
            <div className="text-xs font-semibold text-cyan-400 flex items-center gap-2">
              <Activity className="w-4 h-4" />
              {t('test_section_title')}
            </div>
            <p className="text-xs text-slate-400 mt-0.5">{t('test_desc')}</p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleStartTestRecord}
              disabled={isRecording}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition shadow-lg cursor-pointer ${
                isRecording
                  ? 'bg-rose-600 text-white animate-pulse'
                  : 'bg-cyan-600 hover:bg-cyan-500 text-white shadow-cyan-600/20'
              }`}
            >
              {isRecording ? <Square className="w-3.5 h-3.5" /> : <Mic className="w-3.5 h-3.5" />}
              {isRecording ? `${t('recording')} (${recordSecondsLeft}s)` : t('test_record_btn')}
            </button>

            {recordedAudioUrl && (
              <button
                onClick={handlePlayRecording}
                disabled={isPlayingRecorded}
                className="flex items-center gap-2 px-3.5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold transition"
              >
                <Play className="w-3.5 h-3.5" />
                {t('play_recording')}
              </button>
            )}
          </div>
        </div>

        {/* Dynamic VU-Meter Bar */}
        <div className="space-y-2">
          <div className="flex justify-between text-xs text-slate-400">
            <span>{t('vu_meter')}</span>
            <span className="font-bold text-cyan-400">{Math.round(vuLevel)}%</span>
          </div>

          <div className="h-5 bg-slate-900 rounded-full p-1 border border-slate-800 relative overflow-hidden">
            {/* VAD threshold trigger line */}
            <div
              style={{ left: `${vadThreshold}%` }}
              className="absolute top-0 bottom-0 w-0.5 bg-purple-400 z-10 shadow-[0_0_6px_#a855f7]"
              title={`Soglia VAD: ${vadThreshold}%`}
            />

            {/* Level bar */}
            <div
              style={{ width: `${vuLevel}%` }}
              className={`h-full rounded-full transition-all duration-75 ${
                vuLevel > vadThreshold
                  ? vuLevel > 80
                    ? 'bg-gradient-to-r from-emerald-500 via-amber-400 to-rose-500'
                    : 'bg-gradient-to-r from-cyan-500 to-emerald-400'
                  : 'bg-slate-700'
              }`}
            />
          </div>

          <div className="flex justify-between text-[10px] text-slate-500">
            <span>-60 dB (Silenzio)</span>
            <span className="text-purple-400 font-semibold">Soglia VAD ({vadThreshold}%)</span>
            <span>0 dB (Clipping)</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default View;
