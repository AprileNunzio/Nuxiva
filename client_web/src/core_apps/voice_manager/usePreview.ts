import { useCallback, useEffect, useRef, useState } from 'react';
import { reportError } from '../../shared/errors/errorBus';
import { previewAudio } from './api';

export function usePreview() {
  const [playing, setPlaying] = useState('');
  const audio = useRef<HTMLAudioElement | null>(null);
  const url = useRef('');

  const release = useCallback(() => {
    audio.current?.pause();
    audio.current = null;
    if (url.current) {
      URL.revokeObjectURL(url.current);
      url.current = '';
    }
  }, []);

  useEffect(() => release, [release]);

  const play = useCallback(
    async (voice: string) => {
      release();
      setPlaying(voice);
      try {
        const blob = await previewAudio(voice);
        url.current = URL.createObjectURL(blob);
        const element = new Audio(url.current);
        audio.current = element;
        element.onended = () => setPlaying('');
        await element.play();
      } catch (cause) {
        setPlaying('');
        reportError('voice_manager_preview_failed', cause);
      }
    },
    [release],
  );

  return { playing, play };
}
