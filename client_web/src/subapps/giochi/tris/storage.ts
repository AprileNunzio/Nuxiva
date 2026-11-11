import { SavedGame, ScoreState } from './types';

const SAVES_KEY = 'nuxiva_tris_saves';
const STATS_KEY = 'nuxiva_tris_stats';

export function getSavedGames(): SavedGame[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(SAVES_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function saveGame(game: SavedGame): void {
  if (typeof window === 'undefined') return;
  const current = getSavedGames().filter((item) => item.id !== game.id);
  const updated = [game, ...current].slice(0, 10);
  try {
    localStorage.setItem(SAVES_KEY, JSON.stringify(updated));
  } catch {
  }
}

export function deleteSavedGame(id: string): void {
  if (typeof window === 'undefined') return;
  const filtered = getSavedGames().filter((item) => item.id !== id);
  try {
    localStorage.setItem(SAVES_KEY, JSON.stringify(filtered));
  } catch {
  }
}

export function loadScores(): ScoreState {
  if (typeof window === 'undefined') return { x: 0, o: 0, tie: 0 };
  try {
    const raw = localStorage.getItem(STATS_KEY);
    return raw ? JSON.parse(raw) : { x: 0, o: 0, tie: 0 };
  } catch {
    return { x: 0, o: 0, tie: 0 };
  }
}

export function saveScores(scores: ScoreState): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(STATS_KEY, JSON.stringify(scores));
  } catch {
  }
}
