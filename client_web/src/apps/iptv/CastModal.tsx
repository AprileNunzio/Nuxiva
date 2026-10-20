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
  CheckCircle2,
  RefreshCw,
  X,
  Play,
} from 'lucide-react';
import { getJson, sendJson } from '../shared/http';

export interface TargetDevice {
  id: string;
  kind: 'cast' | 'dlna' | 'sonos' | 'bose' | 'tv' | 'display' | 'pc' | string;
  name: string;
  model?: string;
  online?: boolean;
  active?: boolean;
  volume?: number;
}

interface CastModalProps {
  isOpen: boolean;
  onClose: () => void;
  channelName: string;
  channelId: string;
  channelLogo?: string;
  t: (key: string, vars?: Record<string, string | number>) => string;
}

export const CastModal: React.FC<CastModalProps> = ({
  isOpen,
  onClose,
  channelName,
  channelId,
  channelLogo,
  t,
}) => {
  const [devices, setDevices] = useState<TargetDevice[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeTargetId, setActiveTargetId] = useState<string | null>(null);
  const [castingTarget, setCastingTarget] = useState<TargetDevice | null>(null);
  const [volume, setVolume] = useState<number>(0.6);
  const [isMuted, setIsMuted] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [statusMsg, setStatusMsg] = useState('');

  const fetchDevices = async (discover: boolean = false) => {
    setLoading(true);
    setErrorMsg('');
    try {
      const url = discover ? '/api/tv/targets?discover=true' : '/api/tv/targets';
      const res = await getJson<{ targets: TargetDevice[] }>(url);
      const list = res.targets || [];
      setDevices(list);

      const playing = list.find((d) => d.active);
      if (playing) {
        setCastingTarget(playing);
        setActiveTargetId(playing.id);
        if (typeof playing.volume === 'number') {
          setVolume(playing.volume);
        }
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Impossibile trovare dispositivi');
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

  const handleCastToDevice = async (device: TargetDevice) => {
    setErrorMsg('');
    setStatusMsg(`Connessione e trasmissione su ${device.name}...`);
    try {
      await sendJson('/api/tv/play', 'POST', {
        channel: channelId,
        target: device.id,
      });
      setActiveTargetId(device.id);
      setCastingTarget(device);
      setStatusMsg(`Trasmissione attiva su ${device.name}`);
      setTimeout(() => setStatusMsg(''), 4000);
      void fetchDevices(false);
    } catch (err: any) {
      setErrorMsg(err.message || `Errore trasmissione verso ${device.name}`);
      setStatusMsg('');
    }
  };

  const handleStopCast = async (targetId: string) => {
    setErrorMsg('');
    try {
      await sendJson('/api/tv/stop', 'POST', { target: targetId });
      if (activeTargetId === targetId) {
        setActiveTargetId(null);
        setCastingTarget(null);
      }
      setStatusMsg('Trasmissione interrotta');
      setTimeout(() => setStatusMsg(''), 3000);
      void fetchDevices(false);
    } catch (err: any) {
      setErrorMsg(err.message || 'Errore interruzione');
    }
  };

  const handleVolumeChange = async (targetId: string, newVol: number) => {
    setVolume(newVol);
    try {
      await sendJson('/api/tv/cast/control', 'POST', {
        target: targetId,
        action: 'volume',
        value: newVol,
      });
    } catch (err) {
      // Ignora errori minori di volume
    }
  };

  const getDeviceIcon = (kind: string) => {
    switch (kind) {
      case 'cast':
        return <Cast className="h-5 w-5 text-cyan-400" />;
      case 'sonos':
      case 'bose':
        return <Speaker className="h-5 w-5 text-amber-400" />;
      case 'tv':
      case 'dlna':
        return <Tv className="h-5 w-5 text-sky-400" />;
      case 'pc':
        return <Laptop className="h-5 w-5 text-emerald-400" />;
      case 'display':
      default:
        return <Monitor className="h-5 w-5 text-slate-400" />;
    }
  };

  const getDeviceBadge = (kind: string) => {
    switch (kind) {
      case 'cast':
        return 'Chromecast / Google TV';
      case 'sonos':
        return 'Sonos Sound';
      case 'bose':
        return 'Bose SoundTouch';
      case 'tv':
      case 'dlna':
        return 'Smart TV / DLNA';
      case 'pc':
        return 'PC Mesh Nuxiva';
      case 'display':
      default:
        return 'Schermo Nuxiva';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="flex flex-col w-full max-w-lg rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl overflow-hidden animate-in fade-in duration-200">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 bg-slate-950/60 px-5 py-4">
          <div className="flex items-center gap-2.5">
            <div className="rounded-lg bg-cyan-500/10 border border-cyan-500/30 p-2 text-cyan-400">
              <Cast className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white">Trasmetti su Dispositivo (Cast)</h3>
              <p className="text-xs text-slate-400">
                Chromecast, Google TV, Sonos, Bose, Smart TV, Schermi
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Canale in trasmissione / selezionato */}
        <div className="flex items-center justify-between border-b border-slate-800 bg-slate-900/40 px-5 py-3 text-xs">
          <div className="flex items-center gap-3">
            {channelLogo ? (
              <img
                src={channelLogo}
                alt={channelName}
                className="h-8 w-8 object-contain rounded-md bg-slate-950 p-1 border border-slate-800"
              />
            ) : (
              <div className="flex h-8 w-8 items-center justify-center rounded-md bg-slate-800 font-bold text-cyan-400">
                TV
              </div>
            )}
            <div>
              <span className="block font-bold text-white text-sm">{channelName}</span>
              <span className="text-[11px] text-cyan-400">Flusso IPTV HD Pronto per la trasmissione</span>
            </div>
          </div>
          <button
            type="button"
            onClick={() => void fetchDevices(true)}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800/80 px-2.5 py-1.5 text-xs text-slate-300 hover:text-white hover:bg-slate-700 transition"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Scansiona LAN</span>
          </button>
        </div>

        {/* Feedback messaggi */}
        {statusMsg && (
          <div className="mx-5 mt-3 rounded-lg bg-emerald-950/40 border border-emerald-500/30 px-3 py-2 text-xs text-emerald-300">
            {statusMsg}
          </div>
        )}
        {errorMsg && (
          <div className="mx-5 mt-3 rounded-lg bg-rose-950/40 border border-rose-500/30 px-3 py-2 text-xs text-rose-300">
            {errorMsg}
          </div>
        )}

        {/* Controlli dispositivo attivo se presente */}
        {castingTarget && (
          <div className="m-5 mb-0 rounded-xl border border-cyan-500/40 bg-cyan-950/20 p-3.5 flex flex-col gap-2.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-cyan-500"></span>
                </span>
                <span className="text-xs font-bold text-white">
                  In trasmissione su: {castingTarget.name}
                </span>
              </div>
              <button
                type="button"
                onClick={() => void handleStopCast(castingTarget.id)}
                className="flex items-center gap-1 rounded-lg bg-rose-600/80 hover:bg-rose-600 px-2.5 py-1 text-[11px] font-semibold text-white transition"
              >
                <Square className="h-3 w-3 fill-white" />
                <span>Interrompi</span>
              </button>
            </div>

            {/* Slider volume per il target */}
            <div className="flex items-center gap-2 text-xs text-slate-300">
              <button
                type="button"
                onClick={() => {
                  const nextMute = !isMuted;
                  setIsMuted(nextMute);
                  void handleVolumeChange(castingTarget.id, nextMute ? 0 : volume);
                }}
                className="text-slate-400 hover:text-white"
              >
                {isMuted ? <VolumeX className="h-4 w-4 text-rose-400" /> : <Volume2 className="h-4 w-4" />}
              </button>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={isMuted ? 0 : volume}
                onChange={(e) => void handleVolumeChange(castingTarget.id, Number(e.target.value))}
                className="h-1 flex-1 cursor-pointer accent-cyan-400 rounded-lg bg-slate-800"
              />
              <span className="text-[11px] font-mono text-slate-400">
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
              <p className="text-xs">Ricerca dispositivi Google Cast, Sonos, Bose e Smart TV in corso sulla rete locale...</p>
            </div>
          ) : (
            devices.map((dev) => {
              const isCurrent = activeTargetId === dev.id;
              return (
                <div
                  key={dev.id}
                  onClick={() => !isCurrent && void handleCastToDevice(dev)}
                  className={`flex items-center justify-between rounded-xl border p-3 transition cursor-pointer ${
                    isCurrent
                      ? 'border-cyan-500/50 bg-cyan-950/30'
                      : 'border-slate-800 bg-slate-900/60 hover:border-slate-700 hover:bg-slate-800/50'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className="rounded-lg bg-slate-800 p-2 border border-slate-700">
                      {getDeviceIcon(dev.kind)}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-white">{dev.name}</span>
                        {isCurrent && (
                          <span className="flex items-center gap-1 rounded-full bg-cyan-500/20 px-2 py-0.5 text-[9px] font-bold text-cyan-300 border border-cyan-500/30">
                            Attivo
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 text-[10px] text-slate-400">
                        <span className="text-cyan-400">{getDeviceBadge(dev.kind)}</span>
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
                      className="rounded-lg bg-rose-600/20 hover:bg-rose-600/40 border border-rose-500/30 p-1.5 text-rose-400 transition"
                      title="Interrompi trasmissione"
                    >
                      <Square className="h-4 w-4" />
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        void handleCastToDevice(dev);
                      }}
                      className="flex items-center gap-1 rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-2.5 py-1 text-xs font-semibold text-cyan-300 hover:bg-cyan-500/20 transition"
                    >
                      <Play className="h-3 w-3 fill-cyan-300" />
                      <span>Trasmetti</span>
                    </button>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-slate-800 bg-slate-950/60 px-5 py-3 text-right">
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl bg-slate-800 hover:bg-slate-700 px-4 py-1.5 text-xs font-semibold text-white transition"
          >
            Chiudi
          </button>
        </div>
      </div>
    </div>
  );
};
