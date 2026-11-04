import React, { useEffect, useState } from 'react';
import { SportStep } from '../../types';
import { StepNavigator } from '../../StepNavigator';
import {
  Play,
  Star,
  Tv,
  Calendar,
  Trophy,
  BarChart2,
  Shield,
  Bell,
  RefreshCw,
  Check,
  Flame,
  Volume2,
  Clock,
  Target,
  Zap,
} from 'lucide-react';
import { fetchSportsOverview, saveSportPrefs } from '../../api';

interface HockeyModuleProps {
  readonly onOpenTvChannel?: (channelName: string) => void;
}

interface HockeyTeamStanding {
  readonly rank: number;
  readonly name: string;
  readonly abbr: string;
  readonly division: string;
  readonly gp: number;     // Games Played
  readonly w: number;      // Wins
  readonly l: number;      // Regulation Losses
  readonly otl: number;    // Overtime/Shootout Losses
  readonly pts: number;    // Points (W=2, OTL=1, L=0)
  readonly gf: number;     // Goals For
  readonly ga: number;     // Goals Against
  readonly diff: number;
}

interface HockeyMatch {
  readonly id: string;
  readonly home: string;
  readonly away: string;
  readonly homeScore: number;
  readonly awayScore: number;
  readonly status: 'pre' | 'in' | 'post';
  readonly period: string; // "P1", "P2", "P3", "OT", "SO", "Finale"
  readonly clock: string;
  readonly venue: string;
  readonly tv: string;
  readonly powerPlay?: string; // es. "PP 5v4 Inter"
  readonly goals: readonly { period: string; minute: string; player: string; team: string; type?: string }[];
  readonly sogHome: number; // Shots on goal
  readonly sogAway: number;
}

export const HockeyModule: React.FC<HockeyModuleProps> = ({ onOpenTvChannel }) => {
  const [currentStep, setCurrentStep] = useState<SportStep>('competition');
  const [selectedLeague, setSelectedLeague] = useState<string>('nhl');
  const [selectedDivision, setSelectedDivision] = useState<string>('Atlantic');
  const [favoriteTeams, setFavoriteTeams] = useState<string[]>([
    'New York Rangers',
    'Boston Bruins',
    'Edmonton Oilers',
    'HC Bolzano',
  ]);
  const [voiceAlerts, setVoiceAlerts] = useState<boolean>(true);
  const [goalHornAlerts, setGoalHornAlerts] = useState<boolean>(true);
  const [preferredTvChannel, setPreferredTvChannel] = useState<string>('Sky Sport Arena');
  const [saveSuccess, setSaveSuccess] = useState<boolean>(false);

  // Competizioni Hockey
  const leagues = [
    { code: 'nhl', name: 'NHL (National Hockey League)', flag: '🇺🇸 🇨🇦', count: 32, desc: 'Il campionato di hockey su ghiaccio più prestigioso al mondo' },
    { code: 'iihf', name: 'IIHF World Championship', flag: '🌍', count: 16, desc: 'Campionato Mondiale per Nazionali (Top Division)' },
    { code: 'chl', name: 'Champions Hockey League', flag: '🇪🇺', count: 24, desc: 'Torneo per club dei campioni d’Europa' },
    { code: 'alps_hl', name: 'Alps Hockey League & Serie A', flag: '🇮🇹 🇦🇹', count: 14, desc: 'Campionato italo-austriaco con HC Bolzano, Cortina, Renon, Asiago' },
  ];

  // Partite Hockey Live e Programmate
  const matches: readonly HockeyMatch[] = [
    {
      id: 'h1',
      home: 'New York Rangers',
      away: 'Boston Bruins',
      homeScore: 3,
      awayScore: 2,
      status: 'in',
      period: 'P3',
      clock: "14:22",
      venue: 'Madison Square Garden, New York',
      tv: 'Sky Sport Arena',
      powerPlay: 'Power Play Rangers (5v4)',
      sogHome: 28,
      sogAway: 25,
      goals: [
        { period: 'P1', minute: "08:14", player: 'A. Panarin', team: 'New York Rangers', type: 'EV' },
        { period: 'P1', minute: "17:40", player: 'D. Pastrnak', team: 'Boston Bruins', type: 'PPG' },
        { period: 'P2', minute: "11:05", player: 'M. Zibanejad', team: 'New York Rangers', type: 'PPG' },
        { period: 'P2', minute: "19:12", player: 'B. Marchand', team: 'Boston Bruins', type: 'SHG' },
        { period: 'P3', minute: "04:30", player: 'A. Fox', team: 'New York Rangers', type: 'EV' },
      ],
    },
    {
      id: 'h2',
      home: 'Edmonton Oilers',
      away: 'Colorado Avalanche',
      homeScore: 4,
      awayScore: 3,
      status: 'in',
      period: 'OT',
      clock: "02:45",
      venue: 'Rogers Place, Edmonton',
      tv: 'NHL.tv',
      sogHome: 34,
      sogAway: 31,
      goals: [
        { period: 'P1', minute: "03:10", player: 'C. McDavid', team: 'Edmonton Oilers' },
        { period: 'P2', minute: "07:22", player: 'N. MacKinnon', team: 'Colorado Avalanche' },
        { period: 'P2', minute: "15:45", player: 'L. Draisaitl', team: 'Edmonton Oilers' },
        { period: 'P3', minute: "18:50", player: 'C. Makar', team: 'Colorado Avalanche' },
      ],
    },
    {
      id: 'h3',
      home: 'HC Bolzano',
      away: 'EC Red Bull Salzburg',
      homeScore: 2,
      awayScore: 1,
      status: 'post',
      period: 'Finale',
      clock: '60:00',
      venue: 'Sparkasse Arena, Bolzano',
      tv: 'DAZN',
      sogHome: 27,
      sogAway: 24,
      goals: [
        { period: 'P1', minute: "12:00", player: 'D. Frank', team: 'HC Bolzano' },
        { period: 'P3', minute: "16:40", player: 'L. Frigo', team: 'HC Bolzano' },
      ],
    },
    {
      id: 'h4',
      home: 'Toronto Maple Leafs',
      away: 'Florida Panthers',
      homeScore: 0,
      awayScore: 0,
      status: 'pre',
      period: 'In attesa',
      clock: 'Stanotte 01:00',
      venue: 'Scotiabank Arena, Toronto',
      tv: 'Sky Sport Arena',
      sogHome: 0,
      sogAway: 0,
      goals: [],
    },
  ];

  // Classifiche complete NHL suddivise per Division
  const nhlStandings: readonly HockeyTeamStanding[] = [
    // Atlantic Division
    { rank: 1, name: 'Florida Panthers', abbr: 'FLA', division: 'Atlantic', gp: 12, w: 9, l: 2, otl: 1, pts: 19, gf: 44, ga: 31, diff: +13 },
    { rank: 2, name: 'Boston Bruins', abbr: 'BOS', division: 'Atlantic', gp: 12, w: 8, l: 3, otl: 1, pts: 17, gf: 38, ga: 29, diff: +9 },
    { rank: 3, name: 'Toronto Maple Leafs', abbr: 'TOR', division: 'Atlantic', gp: 11, w: 7, l: 3, otl: 1, pts: 15, gf: 39, ga: 33, diff: +6 },
    { rank: 4, name: 'Tampa Bay Lightning', abbr: 'TBL', division: 'Atlantic', gp: 11, w: 7, l: 4, otl: 0, pts: 14, gf: 41, ga: 35, diff: +6 },
    { rank: 5, name: 'Detroit Red Wings', abbr: 'DET', division: 'Atlantic', gp: 11, w: 5, l: 5, otl: 1, pts: 11, gf: 31, ga: 34, diff: -3 },
    { rank: 6, name: 'Buffalo Sabres', abbr: 'BUF', division: 'Atlantic', gp: 12, w: 4, l: 7, otl: 1, pts: 9, gf: 35, ga: 43, diff: -8 },
    { rank: 7, name: 'Ottawa Senators', abbr: 'OTT', division: 'Atlantic', gp: 10, w: 4, l: 6, otl: 0, pts: 8, gf: 29, ga: 36, diff: -7 },
    { rank: 8, name: 'Montreal Canadiens', abbr: 'MTL', division: 'Atlantic', gp: 11, w: 3, l: 7, otl: 1, pts: 7, gf: 27, ga: 43, diff: -16 },

    // Metropolitan Division
    { rank: 1, name: 'New York Rangers', abbr: 'NYR', division: 'Metropolitan', gp: 11, w: 8, l: 2, otl: 1, pts: 17, gf: 46, ga: 27, diff: +19 },
    { rank: 2, name: 'Carolina Hurricanes', abbr: 'CAR', division: 'Metropolitan', gp: 10, w: 8, l: 2, otl: 0, pts: 16, gf: 40, ga: 24, diff: +16 },
    { rank: 3, name: 'Washington Capitals', abbr: 'WSH', division: 'Metropolitan', gp: 10, w: 7, l: 3, otl: 0, pts: 14, gf: 37, ga: 28, diff: +9 },
    { rank: 4, name: 'New Jersey Devils', abbr: 'NJD', division: 'Metropolitan', gp: 13, w: 6, l: 5, otl: 2, pts: 14, gf: 42, ga: 41, diff: +1 },
    { rank: 5, name: 'New York Islanders', abbr: 'NYI', division: 'Metropolitan', gp: 11, w: 4, l: 5, otl: 2, pts: 10, gf: 26, ga: 32, diff: -6 },
    { rank: 6, name: 'Pittsburgh Penguins', abbr: 'PIT', division: 'Metropolitan', gp: 12, w: 4, l: 7, otl: 1, pts: 9, gf: 34, ga: 48, diff: -14 },
    { rank: 7, name: 'Philadelphia Flyers', abbr: 'PHI', division: 'Metropolitan', gp: 11, w: 4, l: 6, otl: 1, pts: 9, gf: 29, ga: 40, diff: -11 },
    { rank: 8, name: 'Columbus Blue Jackets', abbr: 'CBJ', division: 'Metropolitan', gp: 10, w: 3, l: 6, otl: 1, pts: 7, gf: 30, ga: 37, diff: -7 },

    // Central Division
    { rank: 1, name: 'Winnipeg Jets', abbr: 'WPG', division: 'Central', gp: 11, w: 10, l: 1, otl: 0, pts: 20, gf: 50, ga: 26, diff: +24 },
    { rank: 2, name: 'Dallas Stars', abbr: 'DAL', division: 'Central', gp: 10, w: 7, l: 3, otl: 0, pts: 14, gf: 32, ga: 23, diff: +9 },
    { rank: 3, name: 'Minnesota Wild', abbr: 'MIN', division: 'Central', gp: 10, w: 6, l: 1, otl: 3, pts: 15, gf: 36, ga: 26, diff: +10 },
    { rank: 4, name: 'Colorado Avalanche', abbr: 'COL', division: 'Central', gp: 11, w: 5, l: 6, otl: 0, pts: 10, gf: 37, ga: 44, diff: -7 },
    { rank: 5, name: 'Utah Hockey Club', abbr: 'UTA', division: 'Central', gp: 11, w: 4, l: 5, otl: 2, pts: 10, gf: 31, ga: 38, diff: -7 },
    { rank: 6, name: 'St. Louis Blues', abbr: 'STL', division: 'Central', gp: 11, w: 5, l: 6, otl: 0, pts: 10, gf: 28, ga: 34, diff: -6 },
    { rank: 7, name: 'Nashville Predators', abbr: 'NSH', division: 'Central', gp: 11, w: 3, l: 7, otl: 1, pts: 7, gf: 27, ga: 38, diff: -11 },
    { rank: 8, name: 'Chicago Blackhawks', abbr: 'CHI', division: 'Central', gp: 12, w: 3, l: 7, otl: 2, pts: 8, gf: 31, ga: 39, diff: -8 },

    // Pacific Division
    { rank: 1, name: 'Vegas Golden Knights', abbr: 'VGK', division: 'Pacific', gp: 11, w: 7, l: 3, otl: 1, pts: 15, gf: 48, ga: 34, diff: +14 },
    { rank: 2, name: 'Los Angeles Kings', abbr: 'LAK', division: 'Pacific', gp: 11, w: 6, l: 3, otl: 2, pts: 14, gf: 36, ga: 33, diff: +3 },
    { rank: 3, name: 'Edmonton Oilers', abbr: 'EDM', division: 'Pacific', gp: 11, w: 6, l: 4, otl: 1, pts: 13, gf: 30, ga: 34, diff: -4 },
    { rank: 4, name: 'Vancouver Canucks', abbr: 'VAN', division: 'Pacific', gp: 9, w: 4, l: 2, otl: 3, pts: 11, gf: 28, ga: 28, diff: 0 },
    { rank: 5, name: 'Calgary Flames', abbr: 'CGY', division: 'Pacific', gp: 10, w: 5, l: 4, otl: 1, pts: 11, gf: 31, ga: 32, diff: -1 },
    { rank: 6, name: 'Seattle Kraken', abbr: 'SEA', division: 'Pacific', gp: 11, w: 5, l: 5, otl: 1, pts: 11, gf: 34, ga: 32, diff: +2 },
    { rank: 7, name: 'Anaheim Ducks', abbr: 'ANA', division: 'Pacific', gp: 10, w: 4, l: 4, otl: 2, pts: 10, gf: 23, ga: 29, diff: -6 },
    { rank: 8, name: 'San Jose Sharks', abbr: 'SJS', division: 'Pacific', gp: 12, w: 3, l: 7, otl: 2, pts: 8, gf: 29, ga: 45, diff: -16 },
  ];

  // Caricamento preferenze iniziali
  useEffect(() => {
    fetchSportsOverview()
      .then((res) => {
        const hPrefs = res?.prefs?.household;
        if (hPrefs) {
          if (Array.isArray(hPrefs.favorite_teams) && hPrefs.favorite_teams.length > 0) {
            setFavoriteTeams(hPrefs.favorite_teams);
          }
          if (typeof hPrefs.voice_alerts === 'boolean') setVoiceAlerts(hPrefs.voice_alerts);
          if (hPrefs.preferred_tv_channel) setPreferredTvChannel(hPrefs.preferred_tv_channel);
        }
      })
      .catch(() => {});
  }, []);

  const handleSavePreferences = async (newFavs: string[]) => {
    try {
      await saveSportPrefs('household', {
        default_sport: 'hockey',
        favorite_teams: newFavs,
        voice_alerts: voiceAlerts,
        notify_goals: goalHornAlerts,
        preferred_tv_channel: preferredTvChannel,
      });
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      console.error('Errore salvataggio hockey:', err);
    }
  };

  const toggleFavorite = (teamName: string) => {
    const updated = favoriteTeams.includes(teamName)
      ? favoriteTeams.filter((t) => t !== teamName)
      : [...favoriteTeams, teamName];
    setFavoriteTeams(updated);
    void handleSavePreferences(updated);
  };

  const filteredStandings = nhlStandings.filter((s) => s.division === selectedDivision);

  return (
    <div className="flex flex-col gap-4">
      {/* Step Navigator */}
      <StepNavigator currentStep={currentStep} onSelectStep={setCurrentStep} />

      {/* Banner Salvataggio */}
      {saveSuccess && (
        <div className="flex items-center gap-2 rounded-xl border border-emerald-500/40 bg-emerald-950/40 px-4 py-2.5 text-xs font-semibold text-emerald-700">
          <Check className="h-4 w-4 text-emerald-600" />
          <span>Preferenze Hockey salvate stabilmente su Nuxiva!</span>
        </div>
      )}

      {/* STEP 1: COMPETIZIONI */}
      {currentStep === 'competition' && (
        <div className="flex flex-col gap-4">
          <div className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm">
            <h3 className="text-sm font-bold text-slate-900 mb-1">Campionati e Coppe Mondiali di Hockey</h3>
            <p className="text-xs text-slate-600">
              Dalla leggendaria Stanley Cup della NHL ai tornei mondiali IIHF ed europei della Champions Hockey League.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2">
            {leagues.map((lg) => (
              <div
                key={lg.code}
                onClick={() => {
                  setSelectedLeague(lg.code);
                  setCurrentStep('schedule');
                }}
                className={`flex flex-col justify-between p-4 rounded-2xl border transition-all cursor-pointer ${
                  selectedLeague === lg.code
                    ? 'border-cyan-500/80 bg-gradient-to-r from-cyan-950/40 to-slate-50 shadow-md ring-1 ring-cyan-500/40'
                    : 'border-slate-200 bg-white/80 hover:border-slate-300 hover:bg-slate-100'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-3xl filter drop-shadow">{lg.flag}</span>
                    <div>
                      <h4 className="text-sm font-bold text-slate-900">{lg.name}</h4>
                      <span className="text-xs text-cyan-600 font-semibold">{lg.count} franchigie/squadre</span>
                    </div>
                  </div>
                  <button
                    type="button"
                    className="rounded-xl bg-cyan-600/20 border border-cyan-500/30 px-3 py-1.5 text-xs font-bold text-cyan-700 hover:bg-cyan-600/30 transition"
                  >
                    Esplora
                  </button>
                </div>
                <p className="mt-3 text-xs text-slate-600">{lg.desc}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* STEP 2: CALENDARIO & PARTITE LIVE */}
      {currentStep === 'schedule' && (
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xl">🏒</span>
                <h3 className="text-sm font-bold text-slate-900">Partite & Risultati Live - Periodi & Penalità</h3>
              </div>
              <p className="text-xs text-slate-600 mt-0.5">Marcature per frazione (P1, P2, P3, OT) e situazioni di Power Play</p>
            </div>
            <span className="flex items-center gap-1.5 rounded-full bg-emerald-500/20 border border-emerald-500/30 px-3 py-1 text-xs font-bold text-emerald-600">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-ping" />
              2 Partite Live
            </span>
          </div>

          <div className="flex flex-col gap-3.5">
            {matches.map((m) => (
              <div
                key={m.id}
                className="flex flex-col gap-3 p-4 rounded-2xl border border-slate-200 bg-white/85 hover:border-slate-300 transition"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="flex items-center gap-4 flex-1">
                    <div className="flex flex-col items-center min-w-[75px]">
                      <span
                        className={`text-xs font-bold px-2.5 py-1 rounded-lg ${
                          m.status === 'in'
                            ? 'bg-emerald-500/20 text-emerald-700 border border-emerald-500/40 animate-pulse'
                            : m.status === 'post'
                            ? 'bg-slate-100 text-slate-600'
                            : 'bg-cyan-500/20 text-cyan-700'
                        }`}
                      >
                        {m.period} · {m.clock}
                      </span>
                      <span className="text-[10px] text-slate-500 mt-1 truncate">{m.venue.split(',')[0]}</span>
                    </div>

                    <div className="flex-1">
                      <div className="flex items-center justify-between max-w-sm">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-bold text-slate-900">{m.home}</span>
                          {favoriteTeams.includes(m.home) && (
                            <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-600" />
                          )}
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-xs text-slate-500 font-mono">({m.sogHome} SOG)</span>
                          <span className="text-base font-black font-mono text-cyan-700">{m.homeScore}</span>
                        </div>
                      </div>

                      <div className="flex items-center justify-between max-w-sm mt-1">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-bold text-slate-900">{m.away}</span>
                          {favoriteTeams.includes(m.away) && (
                            <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-600" />
                          )}
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-xs text-slate-500 font-mono">({m.sogAway} SOG)</span>
                          <span className="text-base font-black font-mono text-cyan-700">{m.awayScore}</span>
                        </div>
                      </div>

                      {m.powerPlay && (
                        <div className="mt-2 flex items-center gap-1.5 text-[11px] font-bold text-amber-700">
                          <Zap className="h-3.5 w-3.5 text-amber-600 animate-bounce" />
                          <span>{m.powerPlay}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        if (onOpenTvChannel) onOpenTvChannel(m.tv);
                      }}
                      className="flex items-center gap-1.5 rounded-xl bg-cyan-600 px-3.5 py-2 text-xs font-bold text-white hover:bg-cyan-500 transition shadow-md shadow-cyan-600/20"
                    >
                      <Tv className="h-3.5 w-3.5" />
                      <span>Guarda su {m.tv}</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setCurrentStep('details')}
                      className="rounded-xl border border-slate-300 bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-800 hover:text-slate-900 transition"
                    >
                      Statistiche
                    </button>
                  </div>
                </div>

                {/* Marcature periodi */}
                {m.goals.length > 0 && (
                  <div className="pt-2 border-t border-slate-200/80 flex flex-wrap gap-2 text-[11px] text-slate-600">
                    <span className="font-semibold text-slate-500">Marcature:</span>
                    {m.goals.map((g, idx) => (
                      <span key={idx} className="rounded-md bg-slate-100 px-2 py-0.5 font-mono">
                        🏒 {g.player} ({g.period} {g.minute}) {g.type ? `[${g.type}]` : ''}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* STEP 3: CLASSIFICHE COMPLETE NHL PER DIVISION */}
      {currentStep === 'standings' && (
        <div className="flex flex-col gap-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Classifica Ufficiale NHL per Division (32 Squadre)</h3>
              <p className="text-xs text-slate-600 mt-0.5">Punti: 2 per vittoria (W), 1 per sconfitta OT (OTL), 0 per sconfitta (L)</p>
            </div>

            {/* Selettore Division */}
            <div className="flex flex-wrap items-center gap-1.5 rounded-xl border border-slate-200 bg-slate-50 p-1">
              {['Atlantic', 'Metropolitan', 'Central', 'Pacific'].map((div) => (
                <button
                  key={div}
                  type="button"
                  onClick={() => setSelectedDivision(div)}
                  className={`rounded-lg px-3 py-1 text-xs font-bold transition ${
                    selectedDivision === div
                      ? 'bg-cyan-600 text-white shadow-sm'
                      : 'text-slate-500 hover:text-slate-800'
                  }`}
                >
                  {div}
                </button>
              ))}
            </div>
          </div>

          <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white/80 shadow-md">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50/90 text-[11px] font-bold uppercase text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="py-3 px-3.5">#</th>
                  <th className="py-3 px-3.5">Franchigia</th>
                  <th className="py-3 px-2.5 text-center">GP</th>
                  <th className="py-3 px-2.5 text-center">W</th>
                  <th className="py-3 px-2.5 text-center">L</th>
                  <th className="py-3 px-2.5 text-center">OTL</th>
                  <th className="py-3 px-2.5 text-center">GF</th>
                  <th className="py-3 px-2.5 text-center">GA</th>
                  <th className="py-3 px-2.5 text-center">DIFF</th>
                  <th className="py-3 px-3.5 text-right">Punti</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200/60 font-mono">
                {filteredStandings.map((s, idx) => {
                  const isPlayoff = idx < 3;
                  return (
                    <tr
                      key={s.abbr}
                      className={`hover:bg-slate-800/40 transition ${
                        isPlayoff ? 'bg-cyan-950/15' : ''
                      }`}
                    >
                      <td className="py-3 px-3.5 font-bold">
                        <span
                          className={`inline-block w-5 text-center rounded text-[11px] ${
                            isPlayoff ? 'bg-cyan-500/20 text-cyan-700 font-extrabold' : 'text-slate-500'
                          }`}
                        >
                          {s.rank}
                        </span>
                      </td>
                      <td className="py-3 px-3.5 font-sans font-semibold text-slate-900 flex items-center gap-2">
                        <span className="font-bold text-cyan-700 font-mono text-[11px]">{s.abbr}</span>
                        <span>{s.name}</span>
                        {favoriteTeams.includes(s.name) && (
                          <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-600" />
                        )}
                      </td>
                      <td className="py-3 px-2.5 text-center text-slate-600">{s.gp}</td>
                      <td className="py-3 px-2.5 text-center text-slate-600">{s.w}</td>
                      <td className="py-3 px-2.5 text-center text-slate-600">{s.l}</td>
                      <td className="py-3 px-2.5 text-center text-slate-600">{s.otl}</td>
                      <td className="py-3 px-2.5 text-center text-slate-600">{s.gf}</td>
                      <td className="py-3 px-2.5 text-center text-slate-600">{s.ga}</td>
                      <td className="py-3 px-2.5 text-center text-slate-600">
                        {s.diff > 0 ? `+${s.diff}` : s.diff}
                      </td>
                      <td className="py-3 px-3.5 text-right font-bold text-cyan-700 text-sm">
                        {s.pts}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* STEP 4: DETTAGLI & WIDGET DEDICATI HOCKEY */}
      {currentStep === 'details' && (
        <div className="flex flex-col gap-4">
          <div className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm">
            <h3 className="text-sm font-bold text-slate-900 mb-1">Dettagli di Gara & Widget Tattici Hockey</h3>
            <p className="text-xs text-slate-600">
              Analisi approfondita: tracciatore dei periodi, mappa tiri sul ghiaccio (Slot/Point) e duello tra portieri.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* WIDGET 1: PERIOD & POWER PLAY TRACKER */}
            <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-md flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between border-b border-slate-200 pb-3 mb-3">
                  <div className="flex items-center gap-2">
                    <Clock className="h-4 w-4 text-cyan-600" />
                    <h4 className="text-xs font-bold text-slate-900">Period & Penalty Tracker HUD</h4>
                  </div>
                  <span className="text-[10px] font-mono text-emerald-600 font-bold bg-emerald-500/20 px-2 py-0.5 rounded-full">
                    3° PERIODO (P3)
                  </span>
                </div>

                <div className="flex flex-col gap-3">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-500">Progresso Match (60:00 Reg.)</span>
                    <span className="font-mono font-bold text-slate-900">54:22 / 60:00</span>
                  </div>

                  <div className="grid grid-cols-3 gap-1.5 h-3 rounded-full bg-slate-50 p-0.5 overflow-hidden border border-slate-200">
                    <div className="h-full bg-cyan-500 rounded-sm" title="P1: Concluso" />
                    <div className="h-full bg-cyan-500 rounded-sm" title="P2: Concluso" />
                    <div className="h-full bg-amber-400 rounded-sm animate-pulse" title="P3: In corso" />
                  </div>

                  {/* Box Situazione Power Play attiva */}
                  <div className="mt-2 rounded-xl border border-amber-500/40 bg-amber-950/20 p-3 flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <Zap className="h-5 w-5 text-amber-600 animate-bounce" />
                      <div>
                        <span className="text-xs font-bold text-amber-800 block">Power Play 5v4 Rangers</span>
                        <span className="text-[10px] text-slate-500">Penalità minore: 2 min per Slashing (Bruins)</span>
                      </div>
                    </div>
                    <span className="text-sm font-mono font-black text-amber-700">01:18</span>
                  </div>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-200 flex justify-between text-[11px] text-slate-500">
                <span>Timeout Rangers: 1/1</span>
                <span>Timeout Bruins: 1/1</span>
              </div>
            </div>

            {/* WIDGET 2: RINK SHOT MAP / ZONE RADAR */}
            <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-md flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between border-b border-slate-200 pb-3 mb-3">
                  <div className="flex items-center gap-2">
                    <Target className="h-4 w-4 text-cyan-600" />
                    <h4 className="text-xs font-bold text-slate-900">Rink Shot Map & Distribuzione Tiri</h4>
                  </div>
                  <span className="text-[11px] font-mono text-cyan-600">28 vs 25 SOG</span>
                </div>

                {/* Grafica stilizzata pista da hockey */}
                <div className="relative h-36 rounded-xl border border-cyan-800/40 bg-gradient-to-r from-cyan-950/40 via-slate-50 to-cyan-950/40 p-2 flex items-center justify-between overflow-hidden">
                  {/* Linee di porta e linea rossa centrale */}
                  <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-rose-500/50" />
                  <div className="absolute left-1/3 top-0 bottom-0 w-1 bg-blue-600/60" />
                  <div className="absolute left-1/2 top-0 bottom-0 w-1 bg-rose-600/80" />
                  <div className="absolute right-1/3 top-0 bottom-0 w-1 bg-blue-600/60" />
                  <div className="absolute right-6 top-0 bottom-0 w-0.5 bg-rose-500/50" />

                  {/* Zone Shots Counters */}
                  <div className="relative z-10 flex flex-col items-center justify-center p-2 rounded-lg bg-white/80 border border-slate-300 text-center">
                    <span className="text-[10px] text-slate-500">High Slot</span>
                    <span className="text-xs font-bold text-cyan-700 font-mono">11 tiri</span>
                  </div>
                  <div className="relative z-10 flex flex-col items-center justify-center p-2 rounded-lg bg-white/80 border border-slate-300 text-center">
                    <span className="text-[10px] text-slate-500">Low Slot (Gabbia)</span>
                    <span className="text-xs font-bold text-emerald-600 font-mono">9 tiri (2 gol)</span>
                  </div>
                  <div className="relative z-10 flex flex-col items-center justify-center p-2 rounded-lg bg-white/80 border border-slate-300 text-center">
                    <span className="text-[10px] text-slate-500">Point (Blue Line)</span>
                    <span className="text-xs font-bold text-purple-600 font-mono">8 tiri (1 gol)</span>
                  </div>
                </div>
              </div>

              <div className="mt-3 text-[11px] text-slate-500 flex justify-between">
                <span>Efficienza di realizzazione: 10.7%</span>
                <span>Tiri respinti dalla difesa: 14</span>
              </div>
            </div>

            {/* WIDGET 3: GOALTENDER DUEL */}
            <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-md md:col-span-2">
              <div className="flex items-center justify-between border-b border-slate-200 pb-3 mb-4">
                <div className="flex items-center gap-2">
                  <Shield className="h-4 w-4 text-cyan-600" />
                  <h4 className="text-xs font-bold text-slate-900">Goaltender Duel (Duello tra Portieri)</h4>
                </div>
                <span className="text-xs text-slate-500">Statistiche Parate e Save Percentage (SV%)</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/60 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-950 border border-cyan-800 font-mono font-bold text-cyan-700 text-xs">
                      #31
                    </div>
                    <div>
                      <h5 className="text-xs font-bold text-slate-900">Igor Shesterkin</h5>
                      <span className="text-[10px] text-slate-500">New York Rangers</span>
                    </div>
                  </div>
                  <div className="text-right font-mono">
                    <span className="text-sm font-bold text-emerald-600 block">.920 SV%</span>
                    <span className="text-[10px] text-slate-500">23 Parate / 25 Tiri</span>
                  </div>
                </div>

                <div className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/60 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-950 border border-amber-800 font-mono font-bold text-amber-700 text-xs">
                      #1
                    </div>
                    <div>
                      <h5 className="text-xs font-bold text-slate-900">Jeremy Swayman</h5>
                      <span className="text-[10px] text-slate-500">Boston Bruins</span>
                    </div>
                  </div>
                  <div className="text-right font-mono">
                    <span className="text-sm font-bold text-cyan-600 block">.893 SV%</span>
                    <span className="text-[10px] text-slate-500">25 Parate / 28 Tiri</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* STEP 5: CANALI TV / IPTV COLLEGATI */}
      {currentStep === 'tv_stream' && (
        <div className="flex flex-col gap-4">
          <div className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm">
            <h3 className="text-sm font-bold text-slate-900 mb-1">Canali TV & IPTV per lo Streaming dell'Hockey</h3>
            <p className="text-xs text-slate-600">
              Sintonizzazione automatica immediata con l'applicazione IPTV di Nuxiva.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3.5">
            {[
              { name: 'Sky Sport Arena', desc: 'Dirette esclusive NHL con telecronaca in italiano', icon: '📺' },
              { name: 'NHL.tv', desc: 'Tutte le oltre 1.300 partite della stagione regolare e Playoff', icon: '🏒' },
              { name: 'DAZN', desc: 'Partita della settimana NHL e Alps Hockey League', icon: '⚡' },
              { name: 'Eurosport 1 & 2', desc: 'Mondiali IIHF Top Division e Champions Hockey League', icon: '🌍' },
            ].map((ch) => (
              <div
                key={ch.name}
                className={`flex flex-col justify-between p-4 rounded-2xl border transition ${
                  preferredTvChannel === ch.name
                    ? 'border-cyan-500/80 bg-cyan-950/20 ring-1 ring-cyan-500/40'
                    : 'border-slate-200 bg-white/80 hover:border-slate-300'
                }`}
              >
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-2xl">{ch.icon}</span>
                    <h4 className="text-xs font-bold text-slate-900">{ch.name}</h4>
                  </div>
                  <p className="text-[11px] text-slate-600">{ch.desc}</p>
                </div>

                <div className="mt-4 flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setPreferredTvChannel(ch.name);
                      void saveSportPrefs('household', {
                        default_sport: 'hockey',
                        favorite_teams: favoriteTeams,
                        preferred_tv_channel: ch.name,
                      });
                    }}
                    className={`flex-1 rounded-xl px-3 py-1.5 text-xs font-semibold border transition ${
                      preferredTvChannel === ch.name
                        ? 'bg-cyan-500/20 border-cyan-500/40 text-cyan-700'
                        : 'bg-slate-100 border-slate-300 text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    {preferredTvChannel === ch.name ? 'Canale Predefinito ✓' : 'Imposta Predefinito'}
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      if (onOpenTvChannel) onOpenTvChannel(ch.name);
                    }}
                    className="rounded-xl bg-cyan-600 hover:bg-cyan-500 px-3 py-1.5 text-xs font-bold text-white transition shadow-sm"
                  >
                    <Tv className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* STEP 6: PREFERITI E OPZIONI */}
      {currentStep === 'favorites' && (
        <div className="flex flex-col gap-4 max-w-3xl">
          <div className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm">
            <h3 className="text-sm font-bold text-slate-900 mb-1">Squadre del Cuore & Avvisi Vocali Hockey</h3>
            <p className="text-xs text-slate-600">
              Seleziona le franchigie NHL e squadre che vuoi seguire: Nuxiva ti avvisa a voce e con widget sul desktop quando c'è un gol o inizia una frazione.
            </p>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white/80 p-5 flex flex-col gap-4">
            <h4 className="text-xs font-bold text-slate-900">Opzioni Vocali e Notifiche</h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label className="flex items-center justify-between p-3.5 rounded-xl border border-slate-200 bg-slate-50/60 cursor-pointer">
                <div className="flex items-center gap-3">
                  <Volume2 className="h-5 w-5 text-cyan-600" />
                  <div>
                    <span className="text-xs font-bold text-slate-900 block">Sirena Gol & Annuncio Vocale</span>
                    <span className="text-[10px] text-slate-500">Riproduce il suono della sirena e annuncia il gol</span>
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={goalHornAlerts}
                  onChange={(e) => {
                    setGoalHornAlerts(e.target.checked);
                    void saveSportPrefs('household', {
                      default_sport: 'hockey',
                      favorite_teams: favoriteTeams,
                      voice_alerts: voiceAlerts,
                      notify_goals: e.target.checked,
                      preferred_tv_channel: preferredTvChannel,
                    });
                  }}
                  className="h-4 w-4 rounded accent-cyan-500"
                />
              </label>

              <label className="flex items-center justify-between p-3.5 rounded-xl border border-slate-200 bg-slate-50/60 cursor-pointer">
                <div className="flex items-center gap-3">
                  <Bell className="h-5 w-5 text-amber-600" />
                  <div>
                    <span className="text-xs font-bold text-slate-900 block">Avviso Overtime e Rigori</span>
                    <span className="text-[10px] text-slate-500">Notifica se la partita prosegue ai supplementari</span>
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={voiceAlerts}
                  onChange={(e) => {
                    setVoiceAlerts(e.target.checked);
                    void saveSportPrefs('household', {
                      default_sport: 'hockey',
                      favorite_teams: favoriteTeams,
                      voice_alerts: e.target.checked,
                      notify_goals: goalHornAlerts,
                      preferred_tv_channel: preferredTvChannel,
                    });
                  }}
                  className="h-4 w-4 rounded accent-cyan-500"
                />
              </label>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white/80 p-5">
            <h4 className="text-xs font-bold text-slate-900 mb-3">Franchigie NHL & Squadre Selezionabili</h4>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2.5">
              {[
                'New York Rangers',
                'Boston Bruins',
                'Florida Panthers',
                'Toronto Maple Leafs',
                'Edmonton Oilers',
                'Colorado Avalanche',
                'Vegas Golden Knights',
                'Dallas Stars',
                'Winnipeg Jets',
                'Carolina Hurricanes',
                'Tampa Bay Lightning',
                'HC Bolzano',
                'HC Asiago',
                'SG Cortina',
                'Ritten Sport',
                'HC Pustertal',
              ].map((team) => {
                const isFav = favoriteTeams.includes(team);
                return (
                  <button
                    key={team}
                    type="button"
                    onClick={() => toggleFavorite(team)}
                    className={`flex items-center justify-between p-3 rounded-xl border text-xs font-semibold transition ${
                      isFav
                        ? 'border-amber-500/60 bg-gradient-to-r from-amber-500/20 to-slate-50 text-amber-800 shadow-sm'
                        : 'border-slate-200 bg-slate-50/70 text-slate-600 hover:border-slate-300 hover:text-slate-900'
                    }`}
                  >
                    <span>{team}</span>
                    <Star className={`h-4 w-4 ${isFav ? 'fill-amber-400 text-amber-600' : 'text-slate-600'}`} />
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
