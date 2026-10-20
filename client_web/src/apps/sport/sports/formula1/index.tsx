import React, { useState } from 'react';
import { SportStep } from '../../types';
import { StepNavigator } from '../../StepNavigator';
import { Flag, Trophy, Tv, Star, Timer, Gauge, Bell } from 'lucide-react';

interface Formula1ModuleProps {
  readonly onOpenTvChannel?: (channelName: string) => void;
}

export const Formula1Module: React.FC<Formula1ModuleProps> = ({ onOpenTvChannel }) => {
  const [currentStep, setCurrentStep] = useState<SportStep>('competition');
  const [favoriteDrivers, setFavoriteDrivers] = useState<string[]>(['Charles Leclerc', 'Lewis Hamilton']);

  const grandPrixList = [
    { name: 'Gran Premio d’Italia - Monza', round: 16, country: '🇮🇹', date: 'Settembre', status: 'post' },
    { name: 'Gran Premio degli Stati Uniti - Austin', round: 19, country: '🇺🇸', date: 'Questo Weekend', status: 'in' },
    { name: 'Gran Premio del Messico', round: 20, country: '🇲🇽', date: '27 Ottobre', status: 'pre' },
    { name: 'Gran Premio di Abu Dhabi', round: 24, country: '🇦🇪', date: '8 Dicembre', status: 'pre' },
  ];

  const sessions = [
    { name: 'Prove Libere 1', day: 'Venerdì', time: '19:30', status: 'Concluse', fastest: 'Leclerc (1:33.245)' },
    { name: 'Qualifiche Sprint', day: 'Venerdì', time: '23:30', status: 'Concluse', pole: 'Verstappen (1:32.833)' },
    { name: 'Sprint Race (19 Giri)', day: 'Sabato', time: '20:00', status: 'Conclusa', winner: 'Verstappen' },
    { name: 'Qualifiche Ufficiali', day: 'Sabato', time: '00:00', status: 'Concluse', pole: 'Norris (1:32.330)' },
    { name: 'Gran Premio (56 Giri)', day: 'Domenica', time: '21:00', status: 'LIVE ORA', leader: 'Leclerc (Giro 38/56)' },
  ];

  const driversStandings = [
    { rank: 1, name: 'Max Verstappen', team: 'Red Bull Racing', pts: 354, wins: 7 },
    { rank: 2, name: 'Lando Norris', team: 'McLaren', pts: 297, wins: 3 },
    { rank: 3, name: 'Charles Leclerc', team: 'Scuderia Ferrari', pts: 275, wins: 3 },
    { rank: 4, name: 'Oscar Piastri', team: 'McLaren', pts: 247, wins: 2 },
    { rank: 5, name: 'Carlos Sainz', team: 'Scuderia Ferrari', pts: 215, wins: 1 },
    { rank: 6, name: 'Lewis Hamilton', team: 'Mercedes AMG', pts: 177, wins: 2 },
  ];

  const toggleFavorite = (driver: string) => {
    setFavoriteDrivers((prev) =>
      prev.includes(driver) ? prev.filter((d) => d !== driver) : [...prev, driver]
    );
  };

  return (
    <div className="flex flex-col gap-4">
      <StepNavigator currentStep={currentStep} onSelectStep={setCurrentStep} />

      {/* STEP 1: COMPETIZIONE & GP */}
      {currentStep === 'competition' && (
        <div className="flex flex-col gap-4">
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
            <h3 className="text-sm font-bold text-white mb-1">Campionato Mondiale FIA Formula 1</h3>
            <p className="text-xs text-slate-400">Calendario ufficiale dei 24 Gran Premi, circuiti storici e format Sprint</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {grandPrixList.map((gp) => (
              <div
                key={gp.name}
                onClick={() => setCurrentStep('schedule')}
                className="flex items-center justify-between p-4 rounded-xl border border-slate-800 bg-slate-900/70 hover:border-red-500/50 transition cursor-pointer"
              >
                <div className="flex items-center gap-3">
                  <span className="text-3xl">{gp.country}</span>
                  <div>
                    <h4 className="text-xs font-bold text-white">{gp.name}</h4>
                    <span className="text-[10px] text-slate-400">Round {gp.round} · {gp.date}</span>
                  </div>
                </div>
                <span
                  className={`rounded-full px-2.5 py-1 text-[10px] font-bold ${
                    gp.status === 'in'
                      ? 'bg-red-500/20 text-red-400 animate-pulse'
                      : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  {gp.status === 'in' ? 'IN CORSO' : gp.status.toUpperCase()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* STEP 2: SESSIONI E LIVE */}
      {currentStep === 'schedule' && (
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-900/60 p-4">
            <div>
              <h3 className="text-sm font-bold text-white mb-0.5">Programma Sessioni GP USA - Austin</h3>
              <p className="text-xs text-slate-400">Circuit of the Americas (COTA) · Lunghezza 5.513 km</p>
            </div>
            <span className="flex items-center gap-1.5 rounded-full bg-red-500/20 px-3 py-1 text-xs font-bold text-red-400">
              <span className="h-2 w-2 rounded-full bg-red-400 animate-ping" />
              GARA IN CORSO
            </span>
          </div>

          <div className="flex flex-col gap-2.5">
            {sessions.map((s) => (
              <div
                key={s.name}
                className="flex items-center justify-between p-3.5 rounded-xl border border-slate-800 bg-slate-900/50"
              >
                <div className="flex items-center gap-3">
                  <Timer className="h-4 w-4 text-red-400" />
                  <div>
                    <h4 className="text-xs font-bold text-white">{s.name}</h4>
                    <span className="text-[10px] text-slate-400">{s.day} ore {s.time}</span>
                  </div>
                </div>

                <div className="text-right">
                  <span className="text-xs font-bold text-cyan-300 font-mono">
                    {s.leader || s.winner || s.pole || s.fastest}
                  </span>
                  <p className="text-[10px] text-slate-500">{s.status}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* STEP 3: CLASSIFICHE PILOTI E COSTRUTTORI */}
      {currentStep === 'standings' && (
        <div className="flex flex-col gap-4">
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
            <h3 className="text-sm font-bold text-white mb-1">Classifica Mondiale Piloti</h3>
            <p className="text-xs text-slate-400">Punti iridati, vittorie e podi aggiornati in tempo reale</p>
          </div>

          <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/60">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/80 text-[11px] font-bold uppercase text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-3">Pos</th>
                  <th className="py-2.5 px-3">Pilota</th>
                  <th className="py-2.5 px-3">Scuderia</th>
                  <th className="py-2.5 px-3 text-center">Vittorie</th>
                  <th className="py-2.5 px-3 text-right">Punti</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {driversStandings.map((d) => (
                  <tr key={d.rank} className="hover:bg-slate-800/40 transition">
                    <td className="py-2.5 px-3 font-bold text-slate-400">{d.rank}</td>
                    <td className="py-2.5 px-3 font-sans font-semibold text-white flex items-center gap-2">
                      <span>{d.name}</span>
                      {favoriteDrivers.includes(d.name) && <Star className="h-3 w-3 fill-amber-400 text-amber-400" />}
                    </td>
                    <td className="py-2.5 px-3 font-sans text-slate-300">{d.team}</td>
                    <td className="py-2.5 px-3 text-center text-slate-400">{d.wins}</td>
                    <td className="py-2.5 px-3 text-right font-bold text-red-400">{d.pts}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* STEP 4: TELEMETRIA & GAP */}
      {currentStep === 'details' && (
        <div className="flex flex-col gap-4">
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
            <h3 className="text-sm font-bold text-white mb-1">Live Timing & Telemetria GP Austin</h3>
            <p className="text-xs text-slate-400">Distacchi sui settori, velocità di punta (Speed Trap) e usura gomme</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
              <h4 className="text-xs font-bold text-white mb-3">Leaderboard & Distacchi</h4>
              <div className="flex flex-col gap-2 font-mono text-xs">
                <div className="flex justify-between p-2 rounded-lg bg-red-950/30 border border-red-500/30 text-white font-bold">
                  <span>1. C. Leclerc (Ferrari)</span>
                  <span className="text-red-400">Leader (Giro 38)</span>
                </div>
                <div className="flex justify-between p-2 rounded-lg bg-slate-950 text-slate-200">
                  <span>2. C. Sainz (Ferrari)</span>
                  <span className="text-slate-400">+5.421s</span>
                </div>
                <div className="flex justify-between p-2 rounded-lg bg-slate-950 text-slate-200">
                  <span>3. M. Verstappen (Red Bull)</span>
                  <span className="text-slate-400">+9.840s</span>
                </div>
                <div className="flex justify-between p-2 rounded-lg bg-slate-950 text-slate-200">
                  <span>4. L. Norris (McLaren)</span>
                  <span className="text-slate-400">+12.115s</span>
                </div>
              </div>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
              <h4 className="text-xs font-bold text-white mb-3">Condizioni Pista & Gomme</h4>
              <div className="flex flex-col gap-3 text-xs">
                <div className="flex justify-between py-1 border-b border-slate-800">
                  <span className="text-slate-400">Temperatura Asfalto</span>
                  <span className="font-bold text-white">41.2 °C</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-800">
                  <span className="text-slate-400">Velocità Massima (Speed Trap)</span>
                  <span className="font-bold text-cyan-300">338.4 km/h (Ferrari #16)</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-slate-400">Strategia Gomme Leader</span>
                  <span className="font-bold text-amber-400">Hard (Giro 18) - 1 Sosta</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* STEP 5: CANALE TV IPTV */}
      {currentStep === 'tv_stream' && (
        <div className="flex flex-col gap-4">
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
            <h3 className="text-sm font-bold text-white mb-1">Canali TV & Telecamere Onboard</h3>
            <p className="text-xs text-slate-400">Diretta ufficiale, commento tecnico e feed onboard piloti</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {[
              { name: 'Sky Sport F1 HD', desc: 'Gara in 4K HDR con telecronaca di Carlo Vanzini e Marc Gené' },
              { name: 'Onboard Ferrari #16', desc: 'Telecamera sul casco di Charles Leclerc con team radio live' },
              { name: 'F1 Live Timing Feed', desc: 'Mappa GPS e telemetria con tempi settore per settore' },
            ].map((feed) => (
              <div
                key={feed.name}
                className="flex flex-col justify-between p-4 rounded-xl border border-slate-800 bg-slate-900/70"
              >
                <div>
                  <h4 className="text-xs font-bold text-white mb-1">{feed.name}</h4>
                  <p className="text-[11px] text-slate-400">{feed.desc}</p>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    if (onOpenTvChannel) onOpenTvChannel(feed.name);
                  }}
                  className="mt-4 flex items-center justify-center gap-1.5 rounded-lg bg-red-600 px-3 py-2 text-xs font-bold text-white hover:bg-red-500 transition shadow-sm"
                >
                  <Tv className="h-3.5 w-3.5" />
                  <span>Sintonizza Canale F1</span>
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* STEP 6: PREFERITI E NOTIFICHE */}
      {currentStep === 'favorites' && (
        <div className="flex flex-col gap-4 max-w-2xl">
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
            <h3 className="text-sm font-bold text-white mb-1">Piloti e Scuderie del Cuore</h3>
            <p className="text-xs text-slate-400">Ricevi notifiche quando il tuo pilota fa la pole o sale sul podio</p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {['Charles Leclerc', 'Lewis Hamilton', 'Max Verstappen', 'Lando Norris', 'Carlos Sainz', 'Fernando Alonso'].map(
              (driver) => {
                const isFav = favoriteDrivers.includes(driver);
                return (
                  <button
                    key={driver}
                    type="button"
                    onClick={() => toggleFavorite(driver)}
                    className={`flex items-center justify-between p-3 rounded-lg border text-xs font-semibold transition ${
                      isFav
                        ? 'border-amber-500/50 bg-amber-500/10 text-amber-300'
                        : 'border-slate-800 bg-slate-950 text-slate-400 hover:border-slate-700'
                    }`}
                  >
                    <span>{driver}</span>
                    <Star className={`h-3.5 w-3.5 ${isFav ? 'fill-amber-400 text-amber-400' : ''}`} />
                  </button>
                );
              }
            )}
          </div>
        </div>
      )}
    </div>
  );
};
