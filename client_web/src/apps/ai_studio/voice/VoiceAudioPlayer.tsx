import React, { useEffect, useRef, useState } from 'react';
import { useStudioI18n } from '../scope';
import { fetchVoiceAudio } from './api';

interface VoiceAudioPlayerProps {
  turnId: string;
  available: boolean;
  duration: number;
}

type PlayerState = 'idle' | 'loading' | 'playing' | 'paused' | 'error';

export const VoiceAudioPlayer: React.FC<VoiceAudioPlayerProps> = ({ turnId, available, duration }) => {
  const { t } = useStudioI18n();
  const audio = useRef<HTMLAudioElement | null>(null);
  const url = useRef<string | null>(null);
  const [state, setState] = useState<PlayerState>('idle');
  const [progress, setProgress] = useState(0);

  useEffect(() => () => {
    audio.current?.pause();
    if (url.current) URL.revokeObjectURL(url.current);
  }, []);

  if (!available) {
    return <span className="text-[11px] text-slate-500 italic">{t('voice_no_audio')}</span>;
  }

  const ensure = async (): Promise<HTMLAudioElement> => {
    if (audio.current) return audio.current;
    const blob = await fetchVoiceAudio(turnId);
    url.current = URL.createObjectURL(blob);
    const element = new Audio(url.current);
    element.ontimeupdate = () => setProgress(element.duration ? element.currentTime / element.duration : 0);
    element.onended = () => { setState('paused'); setProgress(0); };
    element.onerror = () => setState('error');
    audio.current = element;
    return element;
  };

  const toggle = async () => {
    if (state === 'playing') {
      audio.current?.pause();
      setState('paused');
      return;
    }
    setState('loading');
    try {
      const element = await ensure();
      await element.play();
      setState('playing');
    } catch (err) {
      console.error(err);
      setState('error');
    }
  };

  const label = state === 'playing' ? t('voice_pause') : state === 'loading' ? t('voice_loading_audio') : t('voice_play');

  return (
    <div className="flex items-center gap-2 w-full min-w-0">
      <button
        type="button"
        onClick={toggle}
        disabled={state === 'loading'}
        aria-label={label}
        className="shrink-0 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-cyan-500/15 hover:bg-cyan-500/25 border border-cyan-500/40 text-cyan-200 text-[11px] font-medium transition-colors disabled:opacity-60"
      >
        <span aria-hidden>{state === 'playing' ? '❚❚' : '▶'}</span>
        <span className="hidden sm:inline">{label}</span>
      </button>
      <div className="flex-1 h-1.5 rounded-full bg-slate-800 overflow-hidden" role="progressbar" aria-valuenow={Math.round(progress * 100)} aria-valuemin={0} aria-valuemax={100}>
        <div className="h-full bg-gradient-to-r from-cyan-400 to-blue-500 transition-[width] duration-150" style={{ width: `${progress * 100}%` }} />
      </div>
      <span className="shrink-0 font-mono text-[10px] text-slate-500">{duration.toFixed(1)}s</span>
      {state === 'error' && <span className="text-[11px] text-rose-400">{t('voice_audio_error')}</span>}
    </div>
  );
};
