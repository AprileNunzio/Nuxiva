import { getJson, sendJson } from '../shared/http';

export interface SportsOverviewResponse {
  leagues: Array<{ code: string; name: string; flag: string; cup: boolean }>;
  people: Array<{ slug: string; name: string; role: string }>;
  prefs: Record<string, SportPreferences>;
  live: Array<any>;
  error?: string | null;
}

export interface SportTeam {
  id: string;
  name: string;
  short: string;
  abbr: string;
  color?: string;
}

export interface StandingRow {
  id: string;
  name: string;
  short: string;
  abbr: string;
  color?: string;
  rank: number;
  played: number;
  points: number;
  won: number;
  drawn: number;
  lost: number;
  diff: number;
}

export interface ScoreboardMatch {
  id: string;
  league: string;
  league_name: string;
  start: string;
  state: 'pre' | 'in' | 'post';
  clock: string;
  detail: string;
  venue: string;
  home: SportTeam & { score?: number | null };
  away: SportTeam & { score?: number | null };
  events?: Array<{
    kind: string;
    minute: string;
    side: string;
    player: string;
    own_goal?: boolean;
    penalty?: boolean;
  }>;
}

export interface SportPreferences {
  default_sport?: string;
  favorite_teams?: string[];
  favorite_driver?: string;
  voice_alerts?: boolean;
  notify_goals?: boolean;
  preferred_tv_channel?: string;
  leagues?: string[];
}

export const fetchSportsOverview = () =>
  getJson<SportsOverviewResponse>('/api/sports');

export const fetchTeams = (league: string) =>
  getJson<{ teams: SportTeam[] }>(`/api/sports/teams/${encodeURIComponent(league)}`);

export const fetchStandings = (league: string) =>
  getJson<{ standings: StandingRow[] }>(`/api/sports/standings/${encodeURIComponent(league)}`);

export const fetchScoreboard = (league: string) =>
  getJson<{ events: ScoreboardMatch[] }>(`/api/sports/scoreboard/${encodeURIComponent(league)}`);

export const fetchF1Schedule = () =>
  getJson<{ races: any[]; next_weekend?: any }>('/api/sports/f1/schedule');

export const fetchF1Results = () =>
  getJson<{ results: any }>('/api/sports/f1/results');

export const saveSportPrefs = (slug: string, prefs: SportPreferences) =>
  sendJson<SportPreferences>(`/api/sports/prefs/${encodeURIComponent(slug)}`, 'PUT', prefs);
