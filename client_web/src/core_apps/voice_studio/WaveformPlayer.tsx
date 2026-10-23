import React, { useEffect, useRef, useState } from 'react';
import { Play, Pause, Download, Volume2, VolumeX } from 'lucide-react';

interface Props {
  src: string;
  title?: string;
  onEnded?: () => void;
}

export const WaveformPlayer: React.FC<Props> = ({ src, title, onEnded }) => {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [muted, setMuted] = useState(false);

  useEffect(() => {
    setIsPlaying(false);
    setCurrentTime(0);
  }, [src]);

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.play().then(() => setIsPlaying(true)).catch(() => {});
    }
  };

  const onTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
    }
  };

  const onLoadedMetadata = () => {
    if (audioRef.current) {
      setDuration(audioRef.current.duration || 0);
    }
  };

  const onSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const time = parseFloat(e.target.value);
    setCurrentTime(time);
    if (audioRef.current) {
      audioRef.current.currentTime = time;
    }
  };

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  const barsCount = 38;
  const progressPercent = duration > 0 ? (currentTime / duration) * 100 : 0;

  return (
    <div className="rounded-2xl border border-slate-300 bg-white p-5 shadow-2xl">
      <audio
        ref={audioRef}
        src={src}
        onTimeUpdate={onTimeUpdate}
        onLoadedMetadata={onLoadedMetadata}
        onEnded={() => {
          setIsPlaying(false);
          if (onEnded) onEnded();
        }}
      />

      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-300 pb-3">
        <span className="text-sm font-bold text-slate-950">
          {title || 'Player Audio Studio'}
        </span>
        <a
          href={src}
          download="voicestudio_output.wav"
          className="flex items-center gap-2 rounded-xl border border-slate-300 bg-slate-100 px-3.5 py-1.5 text-xs font-bold text-slate-950 transition hover:bg-slate-200 hover:border-cyan-400 hover:text-cyan-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 shadow-sm"
          title="Scarica file WAV generato"
        >
          <Download className="h-4 w-4" aria-hidden="true" />
          Scarica WAV
        </a>
      </div>

      {/* Visualizzazione Waveform Fluida */}
      <div
        className="my-4 flex h-16 items-center justify-between gap-1 overflow-hidden rounded-xl border border-slate-200 bg-white px-4"
        aria-hidden="true"
      >
        {Array.from({ length: barsCount }).map((_, i) => {
          const barPercent = (i / barsCount) * 100;
          const isPassed = barPercent <= progressPercent;
          const baseHeight = 25 + Math.sin(i * 0.45) * 18 + Math.cos(i * 0.8) * 12;
          const animatedHeight = isPlaying
            ? Math.max(15, Math.min(95, baseHeight + Math.sin(Date.now() * 0.005 + i) * 16))
            : baseHeight;

          return (
            <div
              key={i}
              className={`w-1.5 rounded-full transition-all duration-100 ${
                isPassed
                  ? 'bg-cyan-400 shadow-sm shadow-cyan-400/60'
                  : 'bg-slate-200'
              }`}
              style={{ height: `${animatedHeight}%` }}
            />
          );
        })}
      </div>

      {/* Barra di avanzamento accessibile */}
      <input
        type="range"
        min={0}
        max={duration || 100}
        step={0.1}
        value={currentTime}
        aria-label="Posizione riproduzione audio"
        aria-valuenow={currentTime}
        aria-valuemin={0}
        aria-valuemax={duration || 100}
        onChange={onSeek}
        className="w-full cursor-pointer accent-cyan-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
      />

      {/* Controlli */}
      <div className="mt-3 flex items-center justify-between text-xs font-semibold text-slate-700">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={togglePlay}
            aria-label={isPlaying ? 'Pausa riproduzione' : 'Avvia riproduzione'}
            className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-500 text-slate-950 shadow-lg shadow-cyan-500/30 transition hover:bg-cyan-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300"
          >
            {isPlaying ? (
              <Pause className="h-5 w-5" aria-hidden="true" />
            ) : (
              <Play className="h-5 w-5 ml-0.5" aria-hidden="true" />
            )}
          </button>
          <button
            type="button"
            onClick={() => {
              if (audioRef.current) {
                audioRef.current.muted = !muted;
                setMuted(!muted);
              }
            }}
            aria-label={muted ? 'Attiva audio' : 'Disattiva audio'}
            className="rounded-lg p-1.5 text-slate-700 transition hover:bg-slate-100 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
          >
            {muted ? <VolumeX className="h-5 w-5 text-rose-600" /> : <Volume2 className="h-5 w-5" />}
          </button>
        </div>

        <div className="font-mono text-xs font-bold text-cyan-700">
          {formatTime(currentTime)} / {formatTime(duration)}
        </div>
      </div>
    </div>
  );
};
