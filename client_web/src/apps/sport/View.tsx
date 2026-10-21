import React, { useEffect, useState } from 'react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { OSAppLayout, OSSidebar, Empty } from '../shared/kit';
import { SportCard, SportId } from './types';
import {
  Trophy,
  ArrowLeft,
  Search,
  Tv,
  ChevronRight,
  Sliders,
  Check,
  Star,
  Volume2,
  Bell,
  X,
} from 'lucide-react';
import { fetchSportsOverview, saveSportPrefs, SportPreferences } from './api';

import { FootballModule } from './sports/football';
import { Formula1Module } from './sports/formula1';
import { MotogpModule } from './sports/motogp';
import { BasketballModule } from './sports/basketball';
import { TennisModule } from './sports/tennis';
import { VolleyballModule } from './sports/volleyball';
import { CyclingModule } from './sports/cycling';
import { CombatModule } from './sports/combat';
import { RugbyModule } from './sports/rugby';
import { NflModule } from './sports/nfl';
import { BaseballModule } from './sports/baseball';
import { AthleticsModule } from './sports/athletics';
import { HockeyModule } from './sports/hockey';

export const View: React.FC = () => {
  const { t } = useScopedI18n('apps/sport');

  const [selectedSport, setSelectedSport] = useState<SportId | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Modale Impostazioni Globali Sport
  const [showSettingsModal, setShowSettingsModal] = useState<boolean>(false);
  const [globalPrefs, setGlobalPrefs] = useState<SportPreferences>({
    default_sport: 'football',
    favorite_teams: ['Inter', 'Napoli', 'Juventus', 'Milan'],
    voice_alerts: true,
    notify_goals: true,
    preferred_tv_channel: 'Sky Sport Calcio HD',
  });
  const [saveStatus, setSaveStatus] = useState<string | null>(null);

  // Carica le preferenze salvate
  useEffect(() => {
    fetchSportsOverview()
      .then((res) => {
        const hPrefs = res?.prefs?.household;
        if (hPrefs) {
          setGlobalPrefs((prev) => ({ ...prev, ...hPrefs }));
          if (hPrefs.default_sport && !selectedSport) {
            // opzionale: se l'utente vuole aprire direttamente il default
          }
        }
      })
      .catch(() => {});
  }, []);

  const handleSaveGlobalPrefs = async () => {
    setSaveStatus('Salvataggio...');
    try {
      await saveSportPrefs('household', globalPrefs);
      setSaveStatus('Preferenze salvate con successo!');
      setTimeout(() => {
        setSaveStatus(null);
        setShowSettingsModal(false);
      }, 1500);
    } catch {
      setSaveStatus('Errore durante il salvataggio');
      setTimeout(() => setSaveStatus(null), 3000);
    }
  };

  const sportsList: readonly SportCard[] = [
    {
      id: 'football',
      nameKey: 'football',
      defaultName: 'Calcio',
      icon: '⚽',
      color: 'emerald',
      gradient: 'from-emerald-900/30 to-slate-900',
      category: 'team',
      activeCompetitions: 12,
      liveNow: true,
      popularLeagues: ['Serie A', 'Champions League', 'Premier League', 'LaLiga'],
    },
    {
      id: 'formula1',
      nameKey: 'formula1',
      defaultName: 'Formula 1',
      icon: '🏎️',
      color: 'red',
      gradient: 'from-red-900/30 to-slate-900',
      category: 'motors',
      activeCompetitions: 1,
      liveNow: true,
      popularLeagues: ['Mondiale Piloti', 'Mondiale Costruttori', 'Sprint Race'],
    },
    {
      id: 'motogp',
      nameKey: 'motogp',
      defaultName: 'MotoGP',
      icon: '🏍️',
      color: 'amber',
      gradient: 'from-amber-900/30 to-slate-900',
      category: 'motors',
      activeCompetitions: 3,
      liveNow: false,
      popularLeagues: ['MotoGP', 'Moto2', 'Moto3'],
    },
    {
      id: 'basketball',
      nameKey: 'basketball',
      defaultName: 'Pallacanestro',
      icon: '🏀',
      color: 'orange',
      gradient: 'from-orange-900/30 to-slate-900',
      category: 'team',
      activeCompetitions: 5,
      liveNow: false,
      popularLeagues: ['NBA', 'EuroLeague', 'LBA Serie A'],
    },
    {
      id: 'tennis',
      nameKey: 'tennis',
      defaultName: 'Tennis',
      icon: '🎾',
      color: 'lime',
      gradient: 'from-lime-900/30 to-slate-900',
      category: 'racket',
      activeCompetitions: 4,
      liveNow: false,
      popularLeagues: ['Nitto ATP Finals', 'Wimbledon', 'Roland Garros'],
    },
    {
      id: 'volleyball',
      nameKey: 'volleyball',
      defaultName: 'Pallavolo',
      icon: '🏐',
      color: 'cyan',
      gradient: 'from-cyan-900/30 to-slate-900',
      category: 'team',
      activeCompetitions: 3,
      liveNow: false,
      popularLeagues: ['SuperLega', 'Serie A1 Femminile', 'CEV Champions'],
    },
    {
      id: 'cycling',
      nameKey: 'cycling',
      defaultName: 'Ciclismo',
      icon: '🚴',
      color: 'yellow',
      gradient: 'from-yellow-900/30 to-slate-900',
      category: 'individual',
      activeCompetitions: 4,
      liveNow: false,
      popularLeagues: ['Giro d’Italia', 'Tour de France', 'Classiche Monumento'],
    },
    {
      id: 'combat',
      nameKey: 'combat',
      defaultName: 'Boxe & MMA',
      icon: '🥊',
      color: 'rose',
      gradient: 'from-rose-900/30 to-slate-900',
      category: 'combat',
      activeCompetitions: 3,
      liveNow: false,
      popularLeagues: ['UFC', 'Mondiale Massimi WBA/WBC', 'Bellator'],
    },
    {
      id: 'rugby',
      nameKey: 'rugby',
      defaultName: 'Rugby',
      icon: '🏉',
      color: 'teal',
      gradient: 'from-teal-900/30 to-slate-900',
      category: 'team',
      activeCompetitions: 3,
      liveNow: false,
      popularLeagues: ['Sei Nazioni', 'Autumn Nations Series', 'URC'],
    },
    {
      id: 'nfl',
      nameKey: 'nfl',
      defaultName: 'Football NFL',
      icon: '🏈',
      color: 'indigo',
      gradient: 'from-indigo-900/30 to-slate-900',
      category: 'team',
      activeCompetitions: 2,
      liveNow: false,
      popularLeagues: ['NFL Regular Season', 'Playoffs & Super Bowl'],
    },
    {
      id: 'baseball',
      nameKey: 'baseball',
      defaultName: 'Baseball MLB',
      icon: '⚾',
      color: 'blue',
      gradient: 'from-blue-900/30 to-slate-900',
      category: 'team',
      activeCompetitions: 2,
      liveNow: false,
      popularLeagues: ['World Series', 'American League', 'National League'],
    },
    {
      id: 'athletics',
      nameKey: 'athletics',
      defaultName: 'Atletica & Nuoto',
      icon: '🏊',
      color: 'sky',
      gradient: 'from-sky-900/30 to-slate-900',
      category: 'individual',
      activeCompetitions: 4,
      liveNow: false,
      popularLeagues: ['Diamond League', 'Mondiali Nuoto', 'Golden Gala'],
    },
    {
      id: 'hockey',
      nameKey: 'hockey',
      defaultName: 'Hockey su Ghiaccio',
      icon: '🏒',
      color: 'blue',
      gradient: 'from-blue-900/30 to-slate-900',
      category: 'team',
      activeCompetitions: 4,
      liveNow: true,
      popularLeagues: ['NHL Stanley Cup', 'IIHF Mondiali', 'Champions Hockey League', 'AlpsHL'],
    },
  ];

  const categories = [
    { id: 'all', label: t('categories_all') },
    { id: 'team', label: t('categories_team') },
    { id: 'motors', label: t('categories_motors') },
    { id: 'racket', label: t('categories_racket') },
    { id: 'combat', label: t('categories_combat') },
    { id: 'individual', label: t('categories_individual') },
  ];

  const filteredSports = sportsList.filter((sp) => {
    if (selectedCategory !== 'all' && sp.category !== selectedCategory) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchName = sp.defaultName.toLowerCase().includes(q);
      const matchLeagues = sp.popularLeagues.some((l) => l.toLowerCase().includes(q));
      return matchName || matchLeagues;
    }
    return true;
  });

  const handleOpenTvChannel = (channelName: string) => {
    alert(`Apertura automatica canale IPTV: ${channelName}`);
  };

  const renderActiveSportModule = () => {
    switch (selectedSport) {
      case 'football':
        return <FootballModule onOpenTvChannel={handleOpenTvChannel} />;
      case 'formula1':
        return <Formula1Module onOpenTvChannel={handleOpenTvChannel} />;
      case 'motogp':
        return <MotogpModule onOpenTvChannel={handleOpenTvChannel} />;
      case 'basketball':
        return <BasketballModule onOpenTvChannel={handleOpenTvChannel} />;
      case 'tennis':
        return <TennisModule onOpenTvChannel={handleOpenTvChannel} />;
      case 'volleyball':
        return <VolleyballModule onOpenTvChannel={handleOpenTvChannel} />;
      case 'cycling':
        return <CyclingModule onOpenTvChannel={handleOpenTvChannel} />;
      case 'combat':
        return <CombatModule onOpenTvChannel={handleOpenTvChannel} />;
      case 'rugby':
        return <RugbyModule onOpenTvChannel={handleOpenTvChannel} />;
      case 'nfl':
        return <NflModule onOpenTvChannel={handleOpenTvChannel} />;
      case 'baseball':
        return <BaseballModule onOpenTvChannel={handleOpenTvChannel} />;
      case 'athletics':
        return <AthleticsModule onOpenTvChannel={handleOpenTvChannel} />;
      case 'hockey':
        return <HockeyModule onOpenTvChannel={handleOpenTvChannel} />;
      default:
        return null;
    }
  };

  const activeSportObj = sportsList.find((s) => s.id === selectedSport);

  const sidebarItems = [
    { id: 'overview', label: t('all_sports'), icon: <Trophy className="h-4 w-4" /> },
    ...sportsList.map((sp) => ({
      id: sp.id,
      label: sp.defaultName,
      count: sp.activeCompetitions,
    })),
  ];

  return (
    <div className="relative h-full w-full select-none overflow-hidden bg-slate-950 text-slate-100">
      <OSAppLayout
        sidebar={
          <OSSidebar
            title={t('title')}
            items={sidebarItems}
            activeId={selectedSport || 'overview'}
            onSelect={(id) => {
              if (id === 'overview') {
                setSelectedSport(null);
              } else {
                setSelectedSport(id as SportId);
              }
            }}
            footer={
              <div className="flex flex-col gap-2 p-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowSettingsModal(true)}
                  className="flex w-full items-center justify-center gap-1.5 rounded-xl border border-slate-750 bg-slate-900/90 hover:bg-slate-850 px-3 py-2 text-xs font-semibold text-slate-200 transition"
                >
                  <Sliders className="h-3.5 w-3.5 text-cyan-400" />
                  <span>Opzioni & Preferenze</span>
                </button>
                <div className="text-[10px] text-slate-400 text-center">
                  13 Discipline con Dirette TV
                </div>
              </div>
            }
          />
        }
        content={
          <div className="flex h-full flex-col overflow-hidden">
            {/* Topbar */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 bg-slate-950/80 p-3.5 backdrop-blur-md">
              <div className="flex items-center gap-3">
                {selectedSport ? (
                  <button
                    type="button"
                    onClick={() => setSelectedSport(null)}
                    className="flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-850 px-3.5 py-1.5 text-xs font-semibold text-slate-200 hover:bg-slate-750 transition"
                  >
                    <ArrowLeft className="h-3.5 w-3.5" />
                    <span>{t('back_to_sports')}</span>
                  </button>
                ) : (
                  <div className="flex items-center gap-2.5">
                    <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-amber-500/10 border border-amber-500/20">
                      <Trophy className="h-4 w-4 text-amber-400" />
                    </div>
                    <div>
                      <h2 className="text-sm font-bold text-white">{t('app_name')}</h2>
                      <span className="text-[11px] text-slate-400">Hub Sportivo con Dati Ufficiali e Canali TV</span>
                    </div>
                  </div>
                )}

                {selectedSport && activeSportObj && (
                  <div className="flex items-center gap-2">
                    <span className="text-xl">{activeSportObj.icon}</span>
                    <span className="text-sm font-bold text-white">{activeSportObj.defaultName}</span>
                  </div>
                )}
              </div>

              <div className="flex items-center gap-2">
                {!selectedSport && (
                  <div className="relative w-64">
                    <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-400" />
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder={t('search_sport')}
                      className="w-full rounded-xl border border-slate-750 bg-slate-900/90 pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-400 focus:border-cyan-500 focus:outline-none"
                    />
                  </div>
                )}

                <button
                  type="button"
                  onClick={() => setShowSettingsModal(true)}
                  className="flex items-center gap-1.5 rounded-xl border border-slate-750 bg-slate-900/90 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:bg-slate-800 hover:text-white transition"
                  title="Preferenze e opzioni predefinite"
                >
                  <Sliders className="h-3.5 w-3.5 text-cyan-400" />
                  <span className="hidden sm:inline">Impostazioni</span>
                </button>
              </div>
            </div>

            {/* Area Contenuto */}
            <div className="flex-1 overflow-y-auto p-4 sm:p-5">
              {selectedSport ? (
                renderActiveSportModule()
              ) : (
                <div className="flex flex-col gap-5">
                  {/* Categorie filtri */}
                  <div className="flex flex-wrap items-center gap-2">
                    {categories.map((c) => (
                      <button
                        key={c.id}
                        type="button"
                        onClick={() => setSelectedCategory(c.id)}
                        className={`rounded-xl px-3.5 py-1.5 text-xs font-bold transition shadow-sm ${
                          selectedCategory === c.id
                            ? 'bg-gradient-to-r from-cyan-600 to-cyan-500 text-white shadow-cyan-500/20'
                            : 'border border-slate-750 bg-slate-900/90 text-slate-300 hover:border-slate-600 hover:text-white'
                        }`}
                      >
                        {c.label}
                      </button>
                    ))}
                  </div>

                  {/* CARDS GRIGLIA SPORT AD ALTO CONTRASTO E VISIBILITA' */}
                  {filteredSports.length === 0 ? (
                    <Empty>Nessuno sport trovato corrispondente alla ricerca.</Empty>
                  ) : (
                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                      {filteredSports.map((sp) => (
                        <div
                          key={sp.id}
                          onClick={() => setSelectedSport(sp.id)}
                          className={`group relative flex flex-col justify-between rounded-2xl border border-slate-750 bg-slate-900/95 p-5 shadow-lg hover:border-cyan-500/70 hover:shadow-cyan-500/10 hover:shadow-2xl transition-all duration-200 cursor-pointer overflow-hidden`}
                        >
                          {/* Accent background soft glow */}
                          <div
                            className={`absolute -right-8 -top-8 h-28 w-28 rounded-full bg-gradient-to-br ${sp.gradient} opacity-20 blur-xl group-hover:opacity-40 transition`}
                          />

                          <div>
                            <div className="flex items-center justify-between">
                              <span className="text-4xl filter drop-shadow-md group-hover:scale-110 transition duration-200">
                                {sp.icon}
                              </span>

                              <span className="flex items-center gap-1.5 rounded-full bg-slate-800 border border-slate-700 px-3 py-1 text-[11px] font-bold text-cyan-300">
                                <Tv className="h-3 w-3 text-cyan-400" />
                                {sp.activeCompetitions} tornei
                              </span>
                            </div>

                            <h3 className="mt-4 text-base font-bold text-white group-hover:text-cyan-300 transition">
                              {sp.defaultName}
                            </h3>

                            <p className="text-xs text-slate-300 mt-1">
                              Scheda a step con classifiche, risultati in tempo reale e canali TV.
                            </p>

                            <div className="mt-3 flex flex-wrap gap-1.5">
                              {sp.popularLeagues.slice(0, 3).map((lg) => (
                                <span
                                  key={lg}
                                  className="rounded-lg bg-slate-800/90 px-2.5 py-1 text-[11px] font-medium text-slate-200 border border-slate-700/60"
                                >
                                  {lg}
                                </span>
                              ))}
                            </div>
                          </div>

                          <div className="mt-5 pt-3.5 border-t border-slate-800 flex items-center justify-between text-xs font-bold text-cyan-400 group-hover:text-cyan-300 transition">
                            <span>Apri Scheda Sport</span>
                            <ChevronRight className="h-4 w-4 transform group-hover:translate-x-1 transition" />
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        }
      />

      {/* MODALE IMPOSTAZIONI GLOBALI SPORT */}
      {showSettingsModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="relative w-full max-w-lg rounded-2xl border border-slate-750 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Sliders className="h-5 w-5 text-cyan-400" />
                <h3 className="text-sm font-bold text-white">Preferenze e Opzioni Sport</h3>
              </div>
              <button
                type="button"
                onClick={() => setShowSettingsModal(false)}
                className="rounded-lg p-1 text-slate-400 hover:text-white"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="mt-4 flex flex-col gap-4 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">Sport Predefinito</label>
                <select
                  value={globalPrefs.default_sport}
                  onChange={(e) => setGlobalPrefs({ ...globalPrefs, default_sport: e.target.value })}
                  className="w-full rounded-xl border border-slate-750 bg-slate-950 px-3 py-2 text-xs text-white focus:border-cyan-500 focus:outline-none"
                >
                  {sportsList.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.icon} {s.defaultName}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Canale TV Predefinito per lo Sport</label>
                <input
                  type="text"
                  value={globalPrefs.preferred_tv_channel || ''}
                  onChange={(e) => setGlobalPrefs({ ...globalPrefs, preferred_tv_channel: e.target.value })}
                  placeholder="Es. Sky Sport Calcio HD o DAZN 1 HD"
                  className="w-full rounded-xl border border-slate-750 bg-slate-950 px-3 py-2 text-xs text-white focus:border-cyan-500 focus:outline-none"
                />
              </div>

              <div className="flex flex-col gap-2 pt-2 border-t border-slate-800">
                <label className="flex items-center justify-between p-3 rounded-xl border border-slate-800 bg-slate-950/60 cursor-pointer">
                  <div className="flex items-center gap-2.5">
                    <Volume2 className="h-4 w-4 text-cyan-400" />
                    <div>
                      <span className="font-semibold text-white block">Annunci Vocali dell'Assistente</span>
                      <span className="text-[10px] text-slate-400">Avvisa vocalmente in casa per inizio gare e gol</span>
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    checked={globalPrefs.voice_alerts}
                    onChange={(e) => setGlobalPrefs({ ...globalPrefs, voice_alerts: e.target.checked })}
                    className="h-4 w-4 rounded accent-cyan-500"
                  />
                </label>

                <label className="flex items-center justify-between p-3 rounded-xl border border-slate-800 bg-slate-950/60 cursor-pointer">
                  <div className="flex items-center gap-2.5">
                    <Bell className="h-4 w-4 text-amber-400" />
                    <div>
                      <span className="font-semibold text-white block">Notifiche Popup Gol in Diretta</span>
                      <span className="text-[10px] text-slate-400">Mostra un banner in tempo reale quando c'è un gol</span>
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    checked={globalPrefs.notify_goals}
                    onChange={(e) => setGlobalPrefs({ ...globalPrefs, notify_goals: e.target.checked })}
                    className="h-4 w-4 rounded accent-cyan-500"
                  />
                </label>
              </div>

              {saveStatus && (
                <div className="rounded-xl bg-cyan-950/50 border border-cyan-500/30 p-2 text-center text-xs text-cyan-300">
                  {saveStatus}
                </div>
              )}
            </div>

            <div className="mt-5 flex items-center justify-end gap-2 border-t border-slate-800 pt-3">
              <button
                type="button"
                onClick={() => setShowSettingsModal(false)}
                className="rounded-xl border border-slate-750 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-800"
              >
                Annulla
              </button>
              <button
                type="button"
                onClick={handleSaveGlobalPrefs}
                className="rounded-xl bg-gradient-to-r from-cyan-600 to-cyan-500 px-5 py-2 text-xs font-bold text-white shadow-md shadow-cyan-600/30 hover:brightness-110"
              >
                Salva Impostazioni
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default View;
