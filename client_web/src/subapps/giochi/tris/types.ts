export type CellValue = 'X' | 'O' | null;

export type GameMode = 'ai' | 'pvp';

export type GameDifficulty = 'easy' | 'medium' | 'hard';

export interface ScoreState {
  x: number;
  o: number;
  tie: number;
}

export interface SavedGame {
  id: string;
  name: string;
  timestamp: number;
  board: CellValue[];
  turn: 'X' | 'O';
  mode: GameMode;
  difficulty: GameDifficulty;
  scores: ScoreState;
}

export interface WinResult {
  winner: 'X' | 'O' | null;
  line: number[] | null;
}
