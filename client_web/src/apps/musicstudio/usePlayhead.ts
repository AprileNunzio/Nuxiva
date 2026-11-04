import { useEffect, useRef, useState, type MutableRefObject } from 'react';
import type { Player } from './engine/player';

export interface Playhead {
  readonly beat: number;
  readonly playing: boolean;
  readonly master: number;
  readonly tracks: ReadonlyMap<string, number>;
}

const IDLE: Playhead = { beat: 0, playing: false, master: 0, tracks: new Map() };

export function usePlayhead(player: MutableRefObject<Player | null>, active: boolean): Playhead {
  const [state, setState] = useState<Playhead>(IDLE);
  const frame = useRef(0);

  useEffect(() => {
    if (!active) return;
    const loop = () => {
      const p = player.current;
      if (p) {
        const meters = p.isPlaying ? p.levels() : { master: 0, tracks: new Map<string, number>() };
        setState({ beat: p.currentBeat(), playing: p.isPlaying, master: meters.master, tracks: meters.tracks });
      }
      frame.current = window.requestAnimationFrame(loop);
    };
    frame.current = window.requestAnimationFrame(loop);
    return () => window.cancelAnimationFrame(frame.current);
  }, [player, active]);

  return state;
}
