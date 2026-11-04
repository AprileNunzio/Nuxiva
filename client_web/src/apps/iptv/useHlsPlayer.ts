import { useEffect, useRef, useState } from 'react';
import { fetchPreview } from './api';

import Hls from 'hls.js';

export function useHlsPlayer(channelId: string | null, isVpnRequired: boolean) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!channelId) {
      setStreamError(null);
      setIsPlaying(false);
      setIsLoading(false);
      return;
    }

    let isDisposed = false;
    let hlsInstance: Hls | null = null;
    setIsLoading(true);
    setStreamError(null);

    const initStream = async () => {
      try {
        // 1. Ottieni il percorso di preview autenticato dal backend (include il token HMAC)
        const previewData = await fetchPreview(channelId).catch(() => ({
          src: `/api/tv/live/${encodeURIComponent(channelId)}`,
          name: '',
        }));

        if (isDisposed) return;
        const video = videoRef.current;
        if (!video) return;

        const src = previewData.src;

        if (Hls && Hls.isSupported()) {
          hlsInstance = new Hls({
            lowLatencyMode: true,
            backBufferLength: 30,
            enableWorker: true,
          });

          hlsInstance.loadSource(src);
          hlsInstance.attachMedia(video);

          hlsInstance.on(Hls.Events.MANIFEST_PARSED, () => {
            if (isDisposed) return;
            video.play().then(() => {
              setIsPlaying(true);
              setIsLoading(false);
            }).catch(() => {
              // Autoplay potrebbe essere bloccato con audio attivo
              video.muted = true;
              video.play().then(() => {
                setIsPlaying(true);
                setIsLoading(false);
              }).catch((e) => {
                setStreamError(`Interazione richiesta per avviare il video: ${e.message}`);
                setIsLoading(false);
              });
            });
          });

          hlsInstance.on(Hls.Events.ERROR, (_event: any, data: any) => {
            if (data.fatal) {
              if (isVpnRequired) {
                setStreamError('Lo streaming IPTV richiede una connessione VPN attiva.');
              } else {
                setStreamError(`Errore riproduzione stream: ${data.details || 'flusso non raggiungibile'}`);
              }
              setIsLoading(false);
              hlsInstance.destroy();
            }
          });
        } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
          // Fallback nativo (Safari / Apple WebKit)
          video.src = src;
          video.play().then(() => {
            setIsPlaying(true);
            setIsLoading(false);
          }).catch(() => {
            video.muted = true;
            video.play().catch((e) => setStreamError(e.message));
          });
        } else {
          setStreamError('Formato video HLS non supportato dal browser.');
          setIsLoading(false);
        }
      } catch (err: any) {
        if (isDisposed) return;
        setStreamError(err?.message || 'Impossibile connettersi allo stream del canale.');
        setIsLoading(false);
      }
    };

    void initStream();

    return () => {
      isDisposed = true;
      if (hlsInstance) {
        try {
          hlsInstance.destroy();
        } catch {
          // ignore
        }
      }
      if (videoRef.current) {
        videoRef.current.pause();
        videoRef.current.removeAttribute('src');
        videoRef.current.load();
      }
    };
  }, [channelId, isVpnRequired]);

  return {
    videoRef,
    streamError,
    isPlaying,
    isLoading,
    setStreamError,
  };
}
