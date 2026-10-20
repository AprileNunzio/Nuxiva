import React, { useState } from 'react';
import { SportStep } from '../types';
import { StepNavigator } from '../StepNavigator';
import { Trophy, Tv, Star, Calendar, BarChart3, Bell } from 'lucide-react';

export interface SportModuleConfig {
  readonly sportName: string;
  readonly sportIcon: string;
  readonly defaultTvChannel: string;
  readonly competitions: readonly { code: string; name: string; flag: string; count?: number }[];
  readonly events: readonly {
    id: string;
    title: string;
    status: 'pre' | 'in' | 'post';
    scoreOrTime: string;
    stage: string;
    venue: string;
    tvChannel: string;
    details?: string;
  }[];
  readonly standings: readonly {
    rank: number;
    name: string;
    teamOrCountry?: string;
    score: string | number;
    details?: string;
  }[];
  readonly defaultFavorites: readonly string[];
}

export function createSportModule(config: SportModuleConfig) {
  return function SportModuleComponent({
    onOpenTvChannel,
  }: {
    readonly onOpenTvChannel?: (channelName: string) => void;
  }) {
    const [currentStep, setCurrentStep] = useState<SportStep>('competition');
    const [selectedComp, setSelectedComp] = useState<string>(config.competitions[0]?.code || '');
    const [favorites, setFavorites] = useState<string[]>([...config.defaultFavorites]);

    const toggleFavorite = (item: string) => {
      setFavorites((prev) =>
        prev.includes(item) ? prev.filter((x) => x !== item) : [...prev, item]
      );
    };

    return (
      <div className="flex flex-col gap-4">
        <StepNavigator currentStep={currentStep} onSelectStep={setCurrentStep} />

        {/* STEP 1: COMPETIZIONI */}
        {currentStep === 'competition' && (
          <div className="flex flex-col gap-4">
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
              <h3 className="text-sm font-bold text-white mb-1">
                {config.sportIcon} Competizioni {config.sportName}
              </h3>
              <p className="text-xs text-slate-400">Tornei principali, campionati e circuiti mondiali</p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              {config.competitions.map((c) => (
                <div
                  key={c.code}
                  onClick={() => {
                    setSelectedComp(c.code);
                    setCurrentStep('schedule');
                  }}
                  className={`flex items-center justify-between p-3.5 rounded-xl border transition cursor-pointer ${
                    selectedComp === c.code
                      ? 'border-cyan-500/80 bg-cyan-950/20 shadow-md ring-1 ring-cyan-500/30'
                      : 'border-slate-800 bg-slate-900/60 hover:border-slate-700 hover:bg-slate-900'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{c.flag}</span>
                    <div>
                      <h4 className="text-xs font-bold text-white">{c.name}</h4>
                      {c.count && <span className="text-[10px] text-slate-400">{c.count} partecipanti</span>}
                    </div>
                  </div>
                  <button
                    type="button"
                    className="rounded-lg bg-cyan-600/20 px-2.5 py-1 text-[11px] font-bold text-cyan-300"
                  >
                    Seleziona
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* STEP 2: CALENDARIO & LIVE */}
        {currentStep === 'schedule' && (
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-900/60 p-4">
              <div>
                <h3 className="text-sm font-bold text-white mb-0.5">Eventi & Live {config.sportName}</h3>
                <p className="text-xs text-slate-400">Calendario e punteggi aggiornati in tempo reale</p>
              </div>
            </div>

            <div className="flex flex-col gap-3">
              {config.events.map((ev) => (
                <div
                  key={ev.id}
                  className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl border border-slate-800 bg-slate-900/60 hover:border-slate-700 transition"
                >
                  <div className="flex items-center gap-4 flex-1">
                    <span
                      className={`text-xs font-bold px-2.5 py-1 rounded-md ${
                        ev.status === 'in'
                          ? 'bg-emerald-500/20 text-emerald-300 animate-pulse'
                          : ev.status === 'post'
                          ? 'bg-slate-800 text-slate-400'
                          : 'bg-cyan-500/20 text-cyan-300'
                      }`}
                    >
                      {ev.scoreOrTime}
                    </span>
                    <div>
                      <h4 className="text-xs font-bold text-white">{ev.title}</h4>
                      <p className="text-[10px] text-slate-400 mt-0.5">
                        {ev.stage} · {ev.venue}
                      </p>
                      {ev.details && <p className="text-[10px] text-cyan-400 mt-1">{ev.details}</p>}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        if (onOpenTvChannel) onOpenTvChannel(ev.tvChannel || config.defaultTvChannel);
                      }}
                      className="flex items-center gap-1.5 rounded-lg bg-cyan-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-cyan-500 transition shadow-sm"
                    >
                      <Tv className="h-3.5 w-3.5" />
                      <span>{ev.tvChannel}</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setCurrentStep('details')}
                      className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-300 hover:text-white"
                    >
                      Dettagli
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* STEP 3: CLASSIFICHE */}
        {currentStep === 'standings' && (
          <div className="flex flex-col gap-4">
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
              <h3 className="text-sm font-bold text-white mb-1">Classifiche Ufficiali - {config.sportName}</h3>
              <p className="text-xs text-slate-400">Punti, posizioni e statistiche</p>
            </div>

            <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/60">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950/80 text-[11px] font-bold uppercase text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="py-2.5 px-3">Pos</th>
                    <th className="py-2.5 px-3">Atleta / Squadra</th>
                    {config.standings[0]?.teamOrCountry && <th className="py-2.5 px-3">Team / Nazione</th>}
                    <th className="py-2.5 px-3 text-right">Punti / Risultato</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {config.standings.map((st) => (
                    <tr key={st.rank} className="hover:bg-slate-800/40 transition">
                      <td className="py-2.5 px-3 font-bold text-slate-400">{st.rank}</td>
                      <td className="py-2.5 px-3 font-sans font-semibold text-white flex items-center gap-2">
                        <span>{st.name}</span>
                        {favorites.includes(st.name) && <Star className="h-3 w-3 fill-amber-400 text-amber-400" />}
                      </td>
                      {st.teamOrCountry && (
                        <td className="py-2.5 px-3 font-sans text-slate-300">{st.teamOrCountry}</td>
                      )}
                      <td className="py-2.5 px-3 text-right font-bold text-cyan-300">{st.score}</td>
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
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
              <h3 className="text-sm font-bold text-white mb-1">Analisi Tecnica e Statistiche Evento</h3>
              <p className="text-xs text-slate-400">Rendimento, parziali e cronaca in tempo reale</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
                <h4 className="text-xs font-bold text-white mb-3">Parziali e Risultati</h4>
                <div className="flex flex-col gap-2 text-xs">
                  {config.events.slice(0, 3).map((ev) => (
                    <div key={ev.id} className="flex justify-between p-2 rounded-lg bg-slate-950 border border-slate-800">
                      <span className="font-semibold text-slate-200">{ev.title}</span>
                      <span className="font-mono text-cyan-400">{ev.scoreOrTime}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
                <h4 className="text-xs font-bold text-white mb-3">Copertura e Canale Ufficiale</h4>
                <p className="text-xs text-slate-300 mb-3">
                  Questo evento è trasmesso in streaming su {config.defaultTvChannel}. Puoi avviare direttamente la riproduzione in alta definizione su Nuxiva.
                </p>
                <button
                  type="button"
                  onClick={() => {
                    if (onOpenTvChannel) onOpenTvChannel(config.defaultTvChannel);
                  }}
                  className="rounded-lg bg-cyan-600 px-4 py-2 text-xs font-bold text-white hover:bg-cyan-500 transition"
                >
                  Avvia Canale TV
                </button>
              </div>
            </div>
          </div>
        )}

        {/* STEP 5: CANALE TV IPTV COLLEGATO */}
        {currentStep === 'tv_stream' && (
          <div className="flex flex-col gap-4">
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
              <h3 className="text-sm font-bold text-white mb-1">Visione Diretta TV / IPTV</h3>
              <p className="text-xs text-slate-400">Canali televisivi e stream dedicati a {config.sportName}</p>
            </div>

            <div className="p-5 rounded-xl border border-cyan-500/40 bg-slate-900/70 max-w-lg">
              <div className="flex items-center gap-3 mb-3">
                <Tv className="h-6 w-6 text-cyan-400" />
                <div>
                  <h4 className="text-sm font-bold text-white">{config.defaultTvChannel}</h4>
                  <p className="text-xs text-slate-400">Canale consigliato per seguire {config.sportName} in diretta</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => {
                  if (onOpenTvChannel) onOpenTvChannel(config.defaultTvChannel);
                }}
                className="w-full rounded-lg bg-cyan-600 px-4 py-2 text-xs font-bold text-white hover:bg-cyan-500 transition shadow-sm"
              >
                Sintonizza adesso su TV / IPTV
              </button>
            </div>
          </div>
        )}

        {/* STEP 6: PREFERITI E NOTIFICHE */}
        {currentStep === 'favorites' && (
          <div className="flex flex-col gap-4 max-w-2xl">
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
              <h3 className="text-sm font-bold text-white mb-1">Preferiti & Notifiche {config.sportName}</h3>
              <p className="text-xs text-slate-400">Scegli gli atleti o le squadre per cui ricevere avvisi vocali istantanei</p>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {config.defaultFavorites.map((fav) => {
                const isFav = favorites.includes(fav);
                return (
                  <button
                    key={fav}
                    type="button"
                    onClick={() => toggleFavorite(fav)}
                    className={`flex items-center justify-between p-3 rounded-lg border text-xs font-semibold transition ${
                      isFav
                        ? 'border-amber-500/50 bg-amber-500/10 text-amber-300'
                        : 'border-slate-800 bg-slate-950 text-slate-400 hover:border-slate-700'
                    }`}
                  >
                    <span>{fav}</span>
                    <Star className={`h-3.5 w-3.5 ${isFav ? 'fill-amber-400 text-amber-400' : ''}`} />
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    );
  };
}
