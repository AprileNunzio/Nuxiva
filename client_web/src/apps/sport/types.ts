export type SportId =
  | 'football'
  | 'formula1'
  | 'motogp'
  | 'basketball'
  | 'tennis'
  | 'volleyball'
  | 'cycling'
  | 'combat'
  | 'rugby'
  | 'nfl'
  | 'baseball'
  | 'athletics'
  | 'hockey';

export type SportStep =
  | 'competition'
  | 'schedule'
  | 'standings'
  | 'details'
  | 'tv_stream'
  | 'favorites';

export interface SportCard {
  readonly id: SportId;
  readonly nameKey: string;
  readonly defaultName: string;
  readonly icon: string;
  readonly color: string;
  readonly gradient: string;
  readonly category: string;
  readonly activeCompetitions: number;
  readonly liveNow: boolean;
  readonly liveEventTitle?: string;
  readonly popularLeagues: readonly string[];
}

export interface Competition {
  readonly id: string;
  readonly code: string;
  readonly name: string;
  readonly flag: string;
  readonly season?: string;
  readonly cup?: boolean;
}

export interface SportEvent {
  readonly id: string;
  readonly competition: string;
  readonly title: string;
  readonly status: 'pre' | 'in' | 'post';
  readonly start_time: number;
  readonly homeTeam?: string;
  readonly awayTeam?: string;
  readonly homeScore?: number | string;
  readonly awayScore?: number | string;
  readonly venue?: string;
  readonly minuteOrLap?: string;
  readonly tvChannel?: string;
  readonly tvChannelId?: string;
  readonly highlights?: readonly string[];
}

export interface StandingRow {
  readonly rank: number;
  readonly name: string;
  readonly code?: string;
  readonly points: number;
  readonly played: number;
  readonly won: number;
  readonly drawn?: number;
  readonly lost: number;
  readonly details?: string;
  readonly form?: readonly ('W' | 'D' | 'L')[];
}
