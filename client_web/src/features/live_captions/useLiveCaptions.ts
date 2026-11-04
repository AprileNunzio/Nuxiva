import { useCallback, useEffect, useRef, useState } from 'react';
import { CaptionEvent, CaptionLine, CaptionsConfig, SpeakerMap } from './types';

const DEFAULTS: CaptionsConfig = {
  enabled: true,
  scope: 'all',
  speaker: true,
  size: 'medium',
  hold: 6,
  position: 'bottom'
};

const SIZES = ['small', 'medium', 'large'] as const;
const POSITIONS = ['bottom', 'center'] as const;
const MAX_LINES = 3;
const STALE_MS = 20000;
const SLUG_RE = /^[a-z0-9][a-z0-9-]{0,40}$/;

export function sanitizeConfig(raw: any): CaptionsConfig {
  const c = raw && typeof raw === 'object' ? raw : {};
  const hold = Number(c.hold);
  const size = SIZES.includes(c.size) ? c.size : DEFAULTS.size;
  const position = POSITIONS.includes(c.position) ? c.position : DEFAULTS.position;
  return {
    enabled: c.enabled !== false,
    scope: c.scope === 'addressed' ? 'addressed' : 'all',
    speaker: c.speaker !== false,
    size,
    hold: Number.isFinite(hold) ? Math.max(2, Math.min(30, hold)) : DEFAULTS.hold,
    position
  };
}

export function computeSpeakerHue(slug: string): number {
  let h = 0;
  for (let i = 0; i < slug.length; i++) {
    h = (h * 31 + slug.charCodeAt(i)) % 360;
  }
  return h;
}

export function useLiveCaptions() {
  const [config, setConfig] = useState<CaptionsConfig>(DEFAULTS);
  const [speakers, setSpeakers] = useState<SpeakerMap>({});
  const [lines, setLines] = useState<CaptionLine[]>([]);
  const lineTimers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());
  const canIdentifyRef = useRef(false);
  const socketRef = useRef<WebSocket | null>(null);
  const activeLinesRef = useRef<Map<string, CaptionLine>>(new Map());

  const commitLines = useCallback(() => {
    setLines(Array.from(activeLinesRef.current.values()));
  }, []);

  const removeLine = useCallback((utt: string) => {
    const timer = lineTimers.current.get(utt);
    if (timer) {
      clearTimeout(timer);
      lineTimers.current.delete(utt);
    }
    if (activeLinesRef.current.has(utt)) {
      activeLinesRef.current.delete(utt);
      commitLines();
    }
  }, [commitLines]);

  const scheduleExpiry = useCallback((utt: string, delayMs: number) => {
    const existing = lineTimers.current.get(utt);
    if (existing) clearTimeout(existing);
    const timer = setTimeout(() => {
      removeLine(utt);
    }, delayMs);
    lineTimers.current.set(utt, timer);
  }, [removeLine]);

  const handleEvent = useCallback((ev: CaptionEvent) => {
    if (!ev || typeof ev !== 'object') return;
    if (ev.type === 'ready') {
      canIdentifyRef.current = Boolean(ev.voiceprint);
      return;
    }
    if (ev.type === 'caption_drop' && typeof ev.utt === 'string') {
      removeLine(ev.utt);
      return;
    }

    const isAddressed = ev.type === 'transcript' || Boolean(ev.addressed);
    if (!config.enabled) return;
    if (config.scope === 'addressed' && !isAddressed) return;

    if (ev.type === 'partial') {
      if (typeof ev.utt !== 'string' || typeof ev.text !== 'string') return;
      const utt = ev.utt;
      const rawWords = ev.text.split(/\s+/).filter(Boolean);
      const stableCount = Number(ev.stable) || 0;
      const speakerSlug = typeof ev.speaker === 'string' && SLUG_RE.test(ev.speaker) ? ev.speaker : '';
      const speakerName = speakerSlug ? (speakers[speakerSlug] || speakerSlug) : '';
      const speakerHue = speakerSlug ? computeSpeakerHue(speakerSlug) : 215;

      const words = rawWords.map((w, idx) => ({
        text: w,
        stable: idx < stableCount
      }));

      const existing = activeLinesRef.current.get(utt);
      const updated: CaptionLine = {
        utt,
        speaker: speakerSlug,
        speakerName,
        speakerHue,
        words,
        addressed: isAddressed,
        final: false,
        done: false
      };

      if (!existing && activeLinesRef.current.size >= MAX_LINES) {
        const oldest = activeLinesRef.current.keys().next().value;
        if (oldest) removeLine(oldest);
      }

      activeLinesRef.current.set(utt, updated);
      commitLines();
      scheduleExpiry(utt, STALE_MS);
      return;
    }

    if (ev.type === 'heard' || ev.type === 'transcript') {
      if (typeof ev.text !== 'string' || !ev.text.trim()) {
        if (ev.utt) removeLine(ev.utt);
        return;
      }
      const utt = typeof ev.utt === 'string' && ev.utt ? ev.utt : `utt-${Date.now()}`;
      const rawWords = ev.text.split(/\s+/).filter(Boolean);
      const speakerSlug = typeof ev.speaker === 'string' && SLUG_RE.test(ev.speaker) ? ev.speaker : '';
      const speakerName = speakerSlug ? (speakers[speakerSlug] || speakerSlug) : '';
      const speakerHue = speakerSlug ? computeSpeakerHue(speakerSlug) : 215;

      const words = rawWords.map(w => ({ text: w, stable: true }));

      const updated: CaptionLine = {
        utt,
        speaker: speakerSlug,
        speakerName,
        speakerHue,
        words,
        addressed: isAddressed,
        final: true,
        done: true
      };

      if (!activeLinesRef.current.has(utt) && activeLinesRef.current.size >= MAX_LINES) {
        const oldest = activeLinesRef.current.keys().next().value;
        if (oldest) removeLine(oldest);
      }

      activeLinesRef.current.set(utt, updated);
      commitLines();
      scheduleExpiry(utt, config.hold * 1000);
    }
  }, [config, speakers, removeLine, commitLines, scheduleExpiry]);

  useEffect(() => {
    let unmounted = false;
    const fetchConfig = async () => {
      try {
        const res = await fetch('/api/ear/config', { cache: 'no-store' });
        if (!res.ok) return;
        const data = await res.json();
        if (unmounted) return;
        if (data.captions) setConfig(sanitizeConfig(data.captions));
        if (data.speakers && typeof data.speakers === 'object') setSpeakers(data.speakers);
      } catch (err) {
        return;
      }
    };
    fetchConfig();
    return () => { unmounted = true; };
  }, []);

  useEffect(() => {
    let unmounted = false;
    let retryDelay = 2500;
    let reconnectTimeout: ReturnType<typeof setTimeout>;

    const connect = () => {
      if (unmounted) return;
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const ws = new WebSocket(`${protocol}//${window.location.host}/ws/ear`);
      socketRef.current = ws;

      ws.onopen = () => {
        retryDelay = 2500;
        try {
          ws.send(JSON.stringify({
            type: 'client',
            page: 'client_web',
            visible: document.visibilityState,
            href: window.location.pathname + window.location.search
          }));
        } catch (e) {
          return;
        }
      };

      ws.onmessage = (event) => {
        try {
          const ev = JSON.parse(event.data) as CaptionEvent;
          handleEvent(ev);
        } catch (e) {
          return;
        }
      };

      ws.onclose = () => {
        if (unmounted) return;
        socketRef.current = null;
        reconnectTimeout = setTimeout(() => {
          retryDelay = Math.min(15000, retryDelay * 1.5);
          connect();
        }, retryDelay);
      };

      ws.onerror = () => {
        try { ws.close(); } catch (e) { return; }
      };
    };

    connect();

    return () => {
      unmounted = true;
      clearTimeout(reconnectTimeout);
      if (socketRef.current) {
        try { socketRef.current.close(); } catch (e) { return; }
        socketRef.current = null;
      }
      lineTimers.current.forEach(timer => clearTimeout(timer));
      lineTimers.current.clear();
      activeLinesRef.current.clear();
    };
  }, [handleEvent]);

  return { lines, config };
}
