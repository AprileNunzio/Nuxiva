import React, { useState, useEffect } from 'react';
import {
  Cast,
  Tv,
  Speaker,
  Monitor,
  Laptop,
  Radio,
  Volume2,
  VolumeX,
  Square,
  RefreshCw,
  X,
  Play,
} from 'lucide-react';
import { getJson, sendJson } from '../shared/http';

export interface MusicOutputDevice {
  id: string;
  kind: 'cast' | 'dlna' | 'sonos' | 'bose' | 'tv' | 'display' | string;
  name: string;
  model?: string;
  manufacturer?: string;
  active?: boolean;
  volume?: number;
  state?: string;
}

interface CastModalProps {
  isOpen: boolean;
  onClose: () => void;
  trackId?: number;
  trackTitle?: string;
  trackArtist?: string;
  t: (key: string, vars?: Record<string, string | number>) => string;
}

export const CastModal: React.FC<CastModalProps> = ({
  isOpen,
  onClose,
  trackId,
  trackTitle,
  trackArtist,
  t,
}) => {
  const [devices, setDevices] = useState<MusicOutputDevice[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeDeviceId, setActiveDeviceId] = useState<string | null>(null);
  const [activeDevice, setActiveDevice] = useState<MusicOutputDevice | null>(null);
  const [volume, setVolume] = useState<number>(0.6);
  const [isMuted, setIsMuted] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [statusMsg, setStatusMsg] = useState('');

  const fetchDevices = async (force: boolean = false) => {
    setLoading(true);
    setErrorMsg('');
    try {
      const url = force ? '/api/music/out?refresh=true' : '/api/music/out';
      const res = await getJson<{ devices: MusicOutputDevice[]; cast: boolean }>(url);
      const list = res.devices || [];
      setDevices(list);

      const playing = list.find((d) => d.active);
      if (playing) {
        setActiveDevice(playing);
        setActiveDeviceId(playing.id);
        if (typeof playing.volume === 'number') {
          setVolume(playing.volume);
        }
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Impossibile trovare dispositivi audio');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      void fetchDevices(true);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleCastPlay = async (device: MusicOutputDevice) => {
    if (!trackId) {
      setErrorMsg('Nessun brano selezionato da trasmettere');
      return;
    }
    setErrorMsg('');
    setStatusMsg(`Connessione a ${device.name}...`);
    try {
      await sendJson(`/api/music/out/${encodeURIComponent(device.id)}/play`, 'POST', {
        tracks: [trackId],
        index: 0,
        start: 0,
        repeat: 'off',
      });
      setActiveDeviceId(device.id);
      setActiveDevice(device);
      setStatusMsg(`Riproduzione attiva su ${device.name}`);
      setTimeout(() => setStatusMsg(''), 4000);
      void fetchDevices(false);
    } catch (err: any) {
      setErrorMsg(err.message || `Errore trasmissione verso ${device.name}`);
      setStatusMsg('');
    }
  };

  const handleStopCast = async (deviceId: string) => {
    setErrorMsg('');
    try {
      await sendJson(`/api/music/out/${encodeURIComponent(deviceId)}/control`, 'POST', { action: 'stop' });
      if (activeDeviceId === deviceId) {
        setActiveDeviceId(null);
        setActiveDevice(null);
      }
      setStatusMsg('Riproduzione remota interrotta');
      setTimeout(() => setStatusMsg(''), 3000);
      void fetchDevices(false);
    } catch (err: any) {
      setErrorMsg(err.message || 'Errore interruzione');
    }
  };

  const handleVolumeChange = async (deviceId: string, newVol: number) => {
    setVolume(newVol);
    try {
      await sendJson(`/api/music/out/${encodeURIComponent(deviceId)}/control`, 'POST', { action: 'volume', value: newVol });
    } catch (err) {
      // Ignora errori minori volume
    }
  };

  const getDeviceIcon = (kind: string) => {
    switch (kind) {
      case 'cast':
        return <Cast className="h-5 w-5 text-sky-600" />;
      case 'sonos':
      case 'bose':
        return <Speaker className="h-5 w-5 text-amber-600" />;
      case 'tv':
      case 'dlna':
        return <Tv className="h-5 w-5 text-cyan-600" />;
      case 'display':
      default:
        return <Monitor className="h-5 w-5 text-slate-500" />;
    }
  };

  const getDeviceBadge = (kind: string) => {
    switch (kind) {
      case 'cast':
        return 'Google Cast Audio / Group';
      case 'sonos':
        return 'Sonos Wireless Hi-Fi';
      case 'bose':
        return 'Bose SoundTouch';
      case 'tv':
      case 'dlna':
        return 'Smart TV / DLNA Speaker';
      case 'display':
      default:
        return 'Schermo Nuxiva';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="flex flex-col w-full max-w-lg rounded-2xl border border-slate-300 bg-white shadow-2xl overflow-hidden animate-in fade-in duration-200">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50/60 px-5 py-4">
          <div className="flex items-center gap-2.5">
            <div className="rounded-lg bg-sky-500/10 border border-sky-500/30 p-2 text-sky-600">
              <Cast className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900">Trasmetti Musica su Dispositivi Audio</h3>
              <p className="text-xs text-slate-500">
                Google Home, Nest Hub, Gruppi Audio, Sonos, Bose, Smart TV
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-900 transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Brano corrente */}
        <div className="flex items-center justify-between border-b border-slate-200 bg-white/40 px-5 py-3 text-xs">
          <div>
            <span className="block font-bold text-slate-900 text-sm">{trackTitle || 'Nessun brano attivo'}</span>
            <span className="text-[11px] text-sky-600">{trackArtist || 'Seleziona un brano o playlist'}</span>
          </div>
          <button
            type="button"
            onClick={() => void fetchDevices(true)}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-lg border border-slate-300 bg-slate-100/80 px-2.5 py-1.5 text-xs text-slate-600 hover:text-slate-900 hover:bg-slate-200 transition"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Scansiona LAN</span>
          </button>
        </div>

        {/* Messaggi */}
        {statusMsg && (
          <div className="mx-5 mt-3 rounded-lg bg-emerald-950/40 border border-emerald-500/30 px-3 py-2 text-xs text-emerald-700">
            {statusMsg}
          </div>
        )}
        {errorMsg && (
          <div className="mx-5 mt-3 rounded-lg bg-rose-950/40 border border-rose-500/30 px-3 py-2 text-xs text-rose-700">
            {errorMsg}
          </div>
        )}

        {/* Controlli dispositivo attivo */}
        {activeDevice && (
          <div className="m-5 mb-0 rounded-xl border border-sky-500/40 bg-sky-950/20 p-3.5 flex flex-col gap-2.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-sky-500"></span>
                </span>
                <span className="text-xs font-bold text-slate-900">
                  Riproduzione su: {activeDevice.name}
                </span>
              </div>
              <button
                type="button"
                onClick={() => void handleStopCast(activeDevice.id)}
                className="flex items-center gap-1 rounded-lg bg-rose-600/80 hover:bg-rose-600 px-2.5 py-1 text-[11px] font-semibold text-white transition"
              >
                <Square className="h-3 w-3 fill-white" />
                <span>Interrompi</span>
              </button>
            </div>

            {/* Slider volume per il target */}
            <div className="flex items-center gap-2 text-xs text-slate-600">
              <button
                type="button"
                onClick={() => {
                  const nextMute = !isMuted;
                  setIsMuted(nextMute);
                  void handleVolumeChange(activeDevice.id, nextMute ? 0 : volume);
                }}
                className="text-slate-500 hover:text-slate-900"
              >
                {isMuted ? <VolumeX className="h-4 w-4 text-rose-600" /> : <Volume2 className="h-4 w-4" />}
              </button>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={isMuted ? 0 : volume}
                onChange={(e) => void handleVolumeChange(activeDevice.id, Number(e.target.value))}
                className="h-1 flex-1 cursor-pointer accent-sky-400 rounded-lg bg-slate-100"
              />
              <span className="text-[11px] font-mono text-slate-500">
                {Math.round((isMuted ? 0 : volume) * 100)}%
              </span>
            </div>
          </div>
        )}

        {/* Lista Dispositivi */}
        <div className="flex-1 overflow-y-auto max-h-72 p-5 flex flex-col gap-2">
          {devices.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-8 text-center text-slate-500">
              <Radio className="h-10 w-10 text-slate-700 animate-pulse mb-2" />
              <p className="text-xs">Ricerca altoparlanti Google Home/Nest, Sonos, Bose e DLNA in corso sulla rete...</p>
            </div>
          ) : (
            devices.map((dev) => {
              const isCurrent = activeDeviceId === dev.id;
              return (
                <div
                  key={dev.id}
                  onClick={() => !isCurrent && void handleCastPlay(dev)}
                  className={`flex items-center justify-between rounded-xl border p-3 transition cursor-pointer ${
                    isCurrent
                      ? 'border-sky-500/50 bg-sky-950/30'
                      : 'border-slate-200 bg-white/60 hover:border-slate-300 hover:bg-slate-100/50'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className="rounded-lg bg-slate-100 p-2 border border-slate-300">
                      {getDeviceIcon(dev.kind)}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-slate-900">{dev.name}</span>
                        {isCurrent && (
                          <span className="flex items-center gap-1 rounded-full bg-sky-500/20 px-2 py-0.5 text-[9px] font-bold text-sky-700 border border-sky-500/30">
                            In riproduzione
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 text-[10px] text-slate-500">
                        <span className="text-sky-600">{getDeviceBadge(dev.kind)}</span>
                        {dev.model && <span>• {dev.model}</span>}
                      </div>
                    </div>
                  </div>

                  {isCurrent ? (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        void handleStopCast(dev.id);
                      }}
                      className="rounded-lg bg-rose-600/20 hover:bg-rose-600/40 border border-rose-500/30 p-1.5 text-rose-600 transition"
                      title="Interrompi"
                    >
                      <Square className="h-4 w-4" />
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        void handleCastPlay(dev);
                      }}
                      className="flex items-center gap-1 rounded-lg border border-sky-500/30 bg-sky-500/10 px-2.5 py-1 text-xs font-semibold text-sky-700 hover:bg-sky-500/20 transition"
                    >
                      <Play className="h-3 w-3 fill-sky-300" />
                      <span>Ascolta qui</span>
                    </button>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-slate-200 bg-slate-50/60 px-5 py-3 text-right">
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl bg-slate-100 hover:bg-slate-200 px-4 py-1.5 text-xs font-semibold text-slate-900 transition"
          >
            Chiudi
          </button>
        </div>
      </div>
    </div>
  );
};
