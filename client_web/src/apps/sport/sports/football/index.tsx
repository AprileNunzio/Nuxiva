import React, { useEffect, useState, useCallback } from 'react';
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
  AlertCircle,
  Volume2,
} from 'lucide-react';
import {
  fetchStandings,
  fetchTeams,
  fetchScoreboard,
  saveSportPrefs,
  fetchSportsOverview,
  SportTeam,
  StandingRow,
  ScoreboardMatch,
} from '../../api';

interface FootballModuleProps {
  readonly onOpenTvChannel?: (channelName: string) => void;
}

// Tutte le 20 squadre reali della Serie A 2024-2025/2026
const SERIE_A_TEAMS_FALLBACK: SportTeam[] = [
  { id: '1', name: 'Atalanta', short: 'Atalanta', abbr: 'ATA' },
  { id: '2', name: 'Bologna', short: 'Bologna', abbr: 'BOL' },
  { id: '3', name: 'Cagliari', short: 'Cagliari', abbr: 'CAG' },
  { id: '4', name: 'Como', short: 'Como', abbr: 'COM' },
  { id: '5', name: 'Empoli', short: 'Empoli', abbr: 'EMP' },
  { id: '6', name: 'Fiorentina', short: 'Fiorentina', abbr: 'FIO' },
  { id: '7', name: 'Genoa', short: 'Genoa', abbr: 'GEN' },
  { id: '8', name: 'Hellas Verona', short: 'Verona', abbr: 'VER' },
  { id: '9', name: 'Inter', short: 'Inter', abbr: 'INT' },
  { id: '10', name: 'Juventus', short: 'Juventus', abbr: 'JUV' },
  { id: '11', name: 'Lazio', short: 'Lazio', abbr: 'LAZ' },
  { id: '12', name: 'Lecce', short: 'Lecce', abbr: 'LEC' },
  { id: '13', name: 'Milan', short: 'Milan', abbr: 'MIL' },
  { id: '14', name: 'Monza', short: 'Monza', abbr: 'MON' },
  { id: '15', name: 'Napoli', short: 'Napoli', abbr: 'NAP' },
  { id: '16', name: 'Parma', short: 'Parma', abbr: 'PAR' },
  { id: '17', name: 'Roma', short: 'Roma', abbr: 'ROM' },
  { id: '18', name: 'Torino', short: 'Torino', abbr: 'TOR' },
  { id: '19', name: 'Udinese', short: 'Udinese', abbr: 'UDI' },
  { id: '20', name: 'Venezia', short: 'Venezia', abbr: 'VEN' },
];

export const FootballModule: React.FC<FootballModuleProps> = ({ onOpenTvChannel }) => {
  const [currentStep, setCurrentStep] = useState<SportStep>('competition');
  const [selectedLeague, setSelectedLeague] = useState<string>('ita.1');
  const [favoriteTeams, setFavoriteTeams] = useState<string[]>(['Inter', 'Napoli', 'Juventus', 'Milan']);
  const [voiceAlerts, setVoiceAlerts] = useState<boolean>(true);
  const [notifyGoals, setNotifyGoals] = useState<boolean>(true);
  const [preferredTvChannel, setPreferredTvChannel] = useState<string>('Sky Sport Calcio HD');

  // Dati reali API
  const [teams, setTeams] = useState<SportTeam[]>(SERIE_A_TEAMS_FALLBACK);
  const [standings, setStandings] = useState<StandingRow[]>([]);
  const [matches, setMatches] = useState<ScoreboardMatch[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [saveSuccess, setSaveSuccess] = useState<boolean>(false);

  const leagues = [
    { code: 'ita.1', name: 'Serie A', flag: '🇮🇹', count: 20 },
    { code: 'ita.2', name: 'Serie B', flag: '🇮🇹', count: 20 },
    { code: 'ita.coppa_italia', name: 'Coppa Italia', flag: '🇮🇹', count: 16 },
    { code: 'uefa.champions', name: 'UEFA Champions League', flag: '🇪🇺', count: 36 },
    { code: 'uefa.europa', name: 'UEFA Europa League', flag: '🇪🇺', count: 36 },
    { code: 'uefa.europa.conf', name: 'UEFA Conference League', flag: '🇪🇺', count: 36 },
    { code: 'eng.1', name: 'Premier League', flag: '🏴󠁧󠁢󠁥󠁮󠁧󠁿', count: 20 },
    { code: 'esp.1', name: 'LaLiga', flag: '🇪🇸', count: 20 },
    { code: 'ger.1', name: 'Bundesliga', flag: '🇩🇪', count: 18 },
    { code: 'fra.1', name: 'Ligue 1', flag: '🇫🇷', count: 18 },
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
          if (typeof hPrefs.notify_goals === 'boolean') setNotifyGoals(hPrefs.notify_goals);
          if (hPrefs.preferred_tv_channel) setPreferredTvChannel(hPrefs.preferred_tv_channel);
        }
      })
      .catch(() => {});
  }, []);

  // Caricamento squadre, classifiche e calendario reali
  const loadLeagueData = useCallback(async (leagueCode: string) => {
    setIsLoading(true);
    try {
      const [tRes, sRes, mRes] = await Promise.allSettled([
        fetchTeams(leagueCode),
        fetchStandings(leagueCode),
        fetchScoreboard(leagueCode),
      ]);

      if (tRes.status === 'fulfilled' && tRes.value?.teams?.length > 0) {
        setTeams(tRes.value.teams);
      } else if (leagueCode === 'ita.1') {
        setTeams(SERIE_A_TEAMS_FALLBACK);
      }

      if (sRes.status === 'fulfilled' && sRes.value?.standings?.length > 0) {
        setStandings(sRes.value.standings);
      } else {
        // Fallback strutturato completo con le squadre se l'API classifica non risponde
        setStandings([]);
      }

      if (mRes.status === 'fulfilled' && mRes.value?.events) {
        setMatches(mRes.value.events);
      } else {
        setMatches([]);
      }
    } catch {
      // Ignora errori
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadLeagueData(selectedLeague);
  }, [selectedLeague, loadLeagueData]);

  // Salvataggio preferenze reale
  const handleSavePreferences = async (newFavs: string[]) => {
    setIsSaving(true);
    setSaveSuccess(false);
    try {
      await saveSportPrefs('household', {
        default_sport: 'football',
        favorite_teams: newFavs,
        voice_alerts: voiceAlerts,
        notify_goals: notifyGoals,
        preferred_tv_channel: preferredTvChannel,
        leagues: [selectedLeague],
      });
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      console.error('Errore salvataggio preferenze sport:', err);
    } finally {
      setIsSaving(false);
    }
  };

  const toggleFavorite = (teamName: string) => {
    const updated = favoriteTeams.includes(teamName)
      ? favoriteTeams.filter((t) => t !== teamName)
      : [...favoriteTeams, teamName];
    setFavoriteTeams(updated);
    void handleSavePreferences(updated);
  };

  const activeLeagueObj = leagues.find((l) => l.code === selectedLeague) || leagues[0];

  return (
    <div className="flex flex-col gap-4">
      {/* Step Navigator */}
      <StepNavigator currentStep={currentStep} onSelectStep={setCurrentStep} />

      {/* Banner Notifica Salvataggio */}
      {saveSuccess && (
        <div className="flex items-center gap-2 rounded-xl border border-emerald-500/40 bg-emerald-950/40 px-4 py-2.5 text-xs font-semibold text-emerald-300">
          <Check className="h-4 w-4 text-emerald-400" />
          <span>Impostazioni e preferenze salvate con successo nel profilo di casa!</span>
        </div>
      )}

      {/* STEP 1: COMPETIZIONI */}
      {currentStep === 'competition' && (
        <div className="flex flex-col gap-4">
          <div className="rounded-2xl border border-slate-750 bg-slate-900/90 p-4 shadow-sm">
            <h3 className="text-sm font-bold text-white mb-1">Campionati e Coppe Ufficiali</h3>
            <p className="text-xs text-slate-300">
              Seleziona la competizione per consultare tutte le squadre, la classifica reale e il calendario delle partite.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3">
            {leagues.map((lg) => (
              <div
                key={lg.code}
                onClick={() => {
                  setSelectedLeague(lg.code);
                  setCurrentStep('schedule');
                }}
                className={`flex items-center justify-between p-4 rounded-2xl border transition-all cursor-pointer ${
                  selectedLeague === lg.code
                    ? 'border-cyan-500/80 bg-gradient-to-r from-cyan-950/40 to-slate-900 shadow-md ring-1 ring-cyan-500/40'
                    : 'border-slate-800 bg-slate-900/80 hover:border-slate-700 hover:bg-slate-850'
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className="text-3xl filter drop-shadow">{lg.flag}</span>
                  <div>
                    <h4 className="text-sm font-bold text-white">{lg.name}</h4>
                    <span className="text-xs text-slate-400">{lg.count} squadre iscritte</span>
                  </div>
                </div>
                <button
                  type="button"
                  className="rounded-xl bg-cyan-600/20 border border-cyan-500/30 px-3 py-1.5 text-xs font-bold text-cyan-300 hover:bg-cyan-600/30 transition"
                >
                  Esplora
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* STEP 2: CALENDARIO & LIVE */}
      {currentStep === 'schedule' && (
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between rounded-2xl border border-slate-750 bg-slate-900/90 p-4 shadow-sm">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xl">{activeLeagueObj.flag}</span>
                <h3 className="text-sm font-bold text-white">{activeLeagueObj.name} - Partite & Calendario Reale</h3>
              </div>
              <p className="text-xs text-slate-300 mt-0.5">Dati in diretta e risultati ufficiali</p>
            </div>
            <button
              type="button"
              onClick={() => void loadLeagueData(selectedLeague)}
              disabled={isLoading}
              className="flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-semibold text-slate-200 hover:bg-slate-750 transition disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin text-cyan-400' : ''}`} />
              <span>Aggiorna</span>
            </button>
          </div>

          {isLoading ? (
            <div className="flex flex-col items-center justify-center p-12 text-slate-400">
              <RefreshCw className="h-8 w-8 animate-spin text-cyan-400 mb-2" />
              <span className="text-xs font-semibold">Caricamento partite ufficiali...</span>
            </div>
          ) : matches.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-8 rounded-2xl border border-slate-800 bg-slate-900/40 text-center">
              <Calendar className="h-10 w-10 text-slate-600 mb-2" />
              <h4 className="text-sm font-bold text-white mb-1">Nessuna partita programmata oggi</h4>
              <p className="text-xs text-slate-400 max-w-md">
                Non ci sono incontri in corso per questa giornata. Consulta la classifica o seleziona un altro campionato.
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              {matches.map((m) => (
                <div
                  key={m.id}
                  className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-2xl border border-slate-800 bg-slate-900/80 hover:border-slate-700 transition"
                >
                  <div className="flex items-center gap-4 flex-1">
                    <div className="flex flex-col items-center min-w-[70px]">
                      <span
                        className={`text-xs font-bold px-2.5 py-1 rounded-lg ${
                          m.state === 'in'
                            ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 animate-pulse'
                            : m.state === 'post'
                            ? 'bg-slate-800 text-slate-300'
                            : 'bg-cyan-500/20 text-cyan-300'
                        }`}
                      >
                        {m.clock || (m.state === 'post' ? 'Finale' : 'In attesa')}
                      </span>
                      {m.venue && <span className="text-[10px] text-slate-400 mt-1 truncate">{m.venue}</span>}
                    </div>

                    <div className="flex-1">
                      <div className="flex items-center justify-between max-w-sm">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-bold text-white">{m.home.name}</span>
                          {favoriteTeams.includes(m.home.name) && (
                            <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
                          )}
                        </div>
                        <span className="text-base font-black font-mono text-cyan-300">
                          {m.home.score !== null && m.home.score !== undefined ? m.home.score : '-'}
                        </span>
                      </div>

                      <div className="flex items-center justify-between max-w-sm mt-1">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-bold text-white">{m.away.name}</span>
                          {favoriteTeams.includes(m.away.name) && (
                            <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
                          )}
                        </div>
                        <span className="text-base font-black font-mono text-cyan-300">
                          {m.away.score !== null && m.away.score !== undefined ? m.away.score : '-'}
                        </span>
                      </div>

                      {m.events && m.events.length > 0 && (
                        <p className="text-[11px] text-slate-300 mt-2 truncate">
                          ⚽ {m.events.map((e) => `${e.player} (${e.minute})`).join(' · ')}
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        if (onOpenTvChannel) onOpenTvChannel(preferredTvChannel);
                      }}
                      className="flex items-center gap-1.5 rounded-xl bg-cyan-600 px-3.5 py-2 text-xs font-bold text-white hover:bg-cyan-500 transition shadow-md shadow-cyan-600/20"
                    >
                      <Tv className="h-3.5 w-3.5" />
                      <span>Guarda Diretta TV</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* STEP 3: CLASSIFICA REALE A 20 SQUADRE */}
      {currentStep === 'standings' && (
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between rounded-2xl border border-slate-750 bg-slate-900/90 p-4 shadow-sm">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xl">{activeLeagueObj.flag}</span>
                <h3 className="text-sm font-bold text-white">{activeLeagueObj.name} - Classifica Ufficiale Completa</h3>
              </div>
              <p className="text-xs text-slate-300 mt-0.5">Tutte le 20 squadre con statistiche ufficiali</p>
            </div>
            <button
              type="button"
              onClick={() => void loadLeagueData(selectedLeague)}
              disabled={isLoading}
              className="flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-semibold text-slate-200 hover:bg-slate-750 transition disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin text-cyan-400' : ''}`} />
              <span>Ricarica</span>
            </button>
          </div>

          <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900/80 shadow-md">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/90 text-[11px] font-bold uppercase text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="py-3 px-3.5">#</th>
                  <th className="py-3 px-3.5">Squadra</th>
                  <th className="py-3 px-3 text-center">G</th>
                  <th className="py-3 px-3 text-center">V</th>
                  <th className="py-3 px-3 text-center">N</th>
                  <th className="py-3 px-3 text-center">P</th>
                  <th className="py-3 px-3 text-center">Diff</th>
                  <th className="py-3 px-3.5 text-right">Punti</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {standings.length > 0
                  ? standings.map((s, idx) => {
                      const rank = s.rank || idx + 1;
                      const isUcl = rank <= 4;
                      const isRelegation = rank >= 18;
                      return (
                        <tr
                          key={s.id || s.name}
                          className={`hover:bg-slate-800/40 transition ${
                            isUcl ? 'bg-cyan-950/10' : isRelegation ? 'bg-rose-950/10' : ''
                          }`}
                        >
                          <td className="py-3 px-3.5 font-bold">
                            <span
                              className={`inline-block w-5 text-center rounded text-[11px] ${
                                isUcl
                                  ? 'bg-cyan-500/20 text-cyan-300 font-extrabold'
                                  : isRelegation
                                  ? 'bg-rose-500/20 text-rose-300'
                                  : 'text-slate-400'
                              }`}
                            >
                              {rank}
                            </span>
                          </td>
                          <td className="py-3 px-3.5 font-sans font-semibold text-white flex items-center gap-2">
                            <span>{s.name}</span>
                            {favoriteTeams.includes(s.name) && (
                              <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
                            )}
                          </td>
                          <td className="py-3 px-3 text-center text-slate-300">{s.played}</td>
                          <td className="py-3 px-3 text-center text-slate-300">{s.won}</td>
                          <td className="py-3 px-3 text-center text-slate-300">{s.drawn}</td>
                          <td className="py-3 px-3 text-center text-slate-300">{s.lost}</td>
                          <td className="py-3 px-3 text-center text-slate-400">
                            {s.diff > 0 ? `+${s.diff}` : s.diff}
                          </td>
                          <td className="py-3 px-3.5 text-right font-bold text-cyan-300 text-sm">
                            {s.points}
                          </td>
                        </tr>
                      );
                    })
                  : teams.map((team, idx) => (
                      <tr key={team.id || team.name} className="hover:bg-slate-800/40 transition">
                        <td className="py-2.5 px-3.5 font-bold text-slate-400">{idx + 1}</td>
                        <td className="py-2.5 px-3.5 font-sans font-semibold text-white flex items-center gap-2">
                          <span>{team.name}</span>
                          {favoriteTeams.includes(team.name) && (
                            <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-center text-slate-400">-</td>
                        <td className="py-2.5 px-3 text-center text-slate-400">-</td>
                        <td className="py-2.5 px-3 text-center text-slate-400">-</td>
                        <td className="py-2.5 px-3 text-center text-slate-400">-</td>
                        <td className="py-2.5 px-3 text-center text-slate-400">-</td>
                        <td className="py-2.5 px-3.5 text-right font-bold text-cyan-300">-</td>
                      </tr>
                    ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* STEP 4: DETTAGLI & STATISTICHE */}
      {currentStep === 'details' && (
        <div className="flex flex-col gap-4">
          <div className="rounded-2xl border border-slate-750 bg-slate-900/90 p-4 shadow-sm">
            <h3 className="text-sm font-bold text-white mb-1">Dettagli & Approfondimenti Squadre</h3>
            <p className="text-xs text-slate-300">
              Visualizza tutte le 20 squadre iscritte con abbreviazioni, colori ufficiali e preferenze salvate.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {teams.map((t) => {
              const isFav = favoriteTeams.includes(t.name);
              return (
                <div
                  key={t.id || t.name}
                  className="flex items-center justify-between p-3.5 rounded-2xl border border-slate-800 bg-slate-900/80 hover:border-slate-700 transition"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-800 border border-slate-700 font-mono font-bold text-cyan-300 text-xs">
                      {t.abbr || t.name.slice(0, 3).toUpperCase()}
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-white">{t.name}</h4>
                      <span className="text-[11px] text-slate-400">{t.short || t.name}</span>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => toggleFavorite(t.name)}
                    className={`rounded-xl p-2 transition ${
                      isFav ? 'text-amber-400 bg-amber-500/10' : 'text-slate-500 hover:text-white hover:bg-slate-800'
                    }`}
                  >
                    <Star className={`h-4 w-4 ${isFav ? 'fill-amber-400' : ''}`} />
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* STEP 5: CANALI TV / IPTV COLLEGATI */}
      {currentStep === 'tv_stream' && (
        <div className="flex flex-col gap-4">
          <div className="rounded-2xl border border-slate-750 bg-slate-900/90 p-4 shadow-sm">
            <h3 className="text-sm font-bold text-white mb-1">Integrazione Diretta Canali IPTV</h3>
            <p className="text-xs text-slate-300">
              Imposta il canale TV predefinito per il calcio e avvia la sintonizzazione istantanea.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {[
              { name: 'Sky Sport Calcio HD', desc: 'Serie A, Premier League, Champions League', icon: '📺' },
              { name: 'DAZN 1 HD', desc: 'Tutte le 10 partite di Serie A per ogni turno', icon: '⚽' },
              { name: 'Rai Sport HD', desc: 'Coppa Italia, Serie C e approfondimenti serali', icon: '🏆' },
              { name: 'Sky Sport 24', desc: 'Notizie no-stop, interviste e formazioni ufficiali', icon: '📰' },
            ].map((ch) => (
              <div
                key={ch.name}
                className={`flex flex-col justify-between p-4 rounded-2xl border transition ${
                  preferredTvChannel === ch.name
                    ? 'border-cyan-500/80 bg-cyan-950/20 ring-1 ring-cyan-500/40'
                    : 'border-slate-800 bg-slate-900/80 hover:border-slate-700'
                }`}
              >
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-2xl">{ch.icon}</span>
                    <h4 className="text-xs font-bold text-white">{ch.name}</h4>
                  </div>
                  <p className="text-[11px] text-slate-300">{ch.desc}</p>
                </div>

                <div className="mt-4 flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setPreferredTvChannel(ch.name);
                      void saveSportPrefs('household', {
                        default_sport: 'football',
                        favorite_teams: favoriteTeams,
                        voice_alerts: voiceAlerts,
                        notify_goals: notifyGoals,
                        preferred_tv_channel: ch.name,
                      });
                    }}
                    className={`flex-1 rounded-xl px-3 py-1.5 text-xs font-semibold border transition ${
                      preferredTvChannel === ch.name
                        ? 'bg-cyan-500/20 border-cyan-500/40 text-cyan-300'
                        : 'bg-slate-800 border-slate-700 text-slate-300 hover:text-white'
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

      {/* STEP 6: PREFERITI & OPZIONI DI DEFAULT */}
      {currentStep === 'favorites' && (
        <div className="flex flex-col gap-4 max-w-3xl">
          <div className="rounded-2xl border border-slate-750 bg-slate-900/90 p-4 shadow-sm">
            <h3 className="text-sm font-bold text-white mb-1">Opzioni, Preferenze e Notifiche</h3>
            <p className="text-xs text-slate-300">
              Personalizza le squadre del cuore, gli annunci vocali e il canale preferito. Tutte le scelte sono salvate stabilmente su Nuxiva.
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5 flex flex-col gap-4">
            <h4 className="text-xs font-bold text-white">Opzioni di Sistema e Notifiche Vocali</h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label className="flex items-center justify-between p-3.5 rounded-xl border border-slate-800 bg-slate-950/60 cursor-pointer">
                <div className="flex items-center gap-3">
                  <Volume2 className="h-5 w-5 text-cyan-400" />
                  <div>
                    <span className="text-xs font-bold text-white block">Annunci Vocali Risultati</span>
                    <span className="text-[10px] text-slate-400">Notifica vocale in casa all'inizio della gara</span>
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={voiceAlerts}
                  onChange={(e) => {
                    setVoiceAlerts(e.target.checked);
                    void saveSportPrefs('household', {
                      default_sport: 'football',
                      favorite_teams: favoriteTeams,
                      voice_alerts: e.target.checked,
                      notify_goals: notifyGoals,
                      preferred_tv_channel: preferredTvChannel,
                    });
                  }}
                  className="h-4 w-4 rounded accent-cyan-500"
                />
              </label>

              <label className="flex items-center justify-between p-3.5 rounded-xl border border-slate-800 bg-slate-950/60 cursor-pointer">
                <div className="flex items-center gap-3">
                  <Bell className="h-5 w-5 text-amber-400" />
                  <div>
                    <span className="text-xs font-bold text-white block">Notifiche Gol in Tempo Reale</span>
                    <span className="text-[10px] text-slate-400">Avviso a comparsa quando segna la tua squadra</span>
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={notifyGoals}
                  onChange={(e) => {
                    setNotifyGoals(e.target.checked);
                    void saveSportPrefs('household', {
                      default_sport: 'football',
                      favorite_teams: favoriteTeams,
                      voice_alerts: voiceAlerts,
                      notify_goals: e.target.checked,
                      preferred_tv_channel: preferredTvChannel,
                    });
                  }}
                  className="h-4 w-4 rounded accent-cyan-500"
                />
              </label>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
            <h4 className="text-xs font-bold text-white mb-3">Tutte le 20 Squadre della Serie A</h4>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2.5">
              {teams.map((team) => {
                const isFav = favoriteTeams.includes(team.name);
                return (
                  <button
                    key={team.id || team.name}
                    type="button"
                    onClick={() => toggleFavorite(team.name)}
                    className={`flex items-center justify-between p-3 rounded-xl border text-xs font-semibold transition ${
                      isFav
                        ? 'border-amber-500/60 bg-gradient-to-r from-amber-500/20 to-slate-900 text-amber-200 shadow-sm'
                        : 'border-slate-800 bg-slate-950/70 text-slate-300 hover:border-slate-700 hover:text-white'
                    }`}
                  >
                    <span>{team.name}</span>
                    <Star className={`h-4 w-4 ${isFav ? 'fill-amber-400 text-amber-400' : 'text-slate-600'}`} />
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
