import React, { useState } from 'react';
import { BrainTargetConfig } from '../types';
import { TargetCard } from './TargetCard';
import {
  Brain,
  Search,
  Key,
  HardDrive,
  Server,
  Sparkles,
  Users,
  Radio,
} from 'lucide-react';

interface MainDashboardProps {
  readonly targets: readonly BrainTargetConfig[];
  readonly onSelectTarget: (target: BrainTargetConfig) => void;
  readonly t: (key: string) => string;
}

export const MainDashboard: React.FC<MainDashboardProps> = ({ targets, onSelectTarget, t }) => {
  const [filterQuery, setFilterQuery] = useState('');
  const [methodFilter, setMethodFilter] = useState<'all' | 'api_key' | 'ollama_local' | 'ollama_remote'>('all');

  const fastConversation = targets.find((t) => t.id === 'fast_conversation') || targets[0];
  const reasoning = targets.find((t) => t.id === 'reasoning') || targets[1];
  const liveAudio = targets.find((t) => t.id === 'live_audio');
  const ceo = targets.find((t) => t.id === 'ceo');
  const teamAgents = targets.filter((t) => t.category === 'agent');

  const filteredAgents = teamAgents.filter((agent) => {
    const matchesQuery =
      agent.name.toLowerCase().includes(filterQuery.toLowerCase()) ||
      agent.assignedModel.toLowerCase().includes(filterQuery.toLowerCase()) ||
      agent.id.toLowerCase().includes(filterQuery.toLowerCase());
    const matchesMethod = methodFilter === 'all' || agent.method === methodFilter;
    return matchesQuery && matchesMethod;
  });

  const apiCount = targets.filter((t) => t.method === 'api_key').length;
  const localCount = targets.filter((t) => t.method === 'ollama_local').length;
  const remoteCount = targets.filter((t) => t.method === 'ollama_remote').length;

  return (
    <div className="w-full space-y-8 pb-12">
      {/* Overview Stats Bar (Material Design 3 Light Tonal Cards) */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5 w-full">
        <div className="rounded-2xl border border-slate-200/90 bg-white p-4.5 flex items-center justify-between shadow-2xs hover:shadow-sm transition">
          <div>
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
              {t('total_assigned')}
            </span>
            <span className="text-2xl sm:text-3xl font-black text-slate-950 mt-0.5 block">{targets.length}</span>
          </div>
          <div className="w-11 h-11 rounded-2xl bg-indigo-50 border border-indigo-100 text-indigo-700 flex items-center justify-center font-black shadow-2xs">
            <Brain className="w-5 h-5" />
          </div>
        </div>

        <div className="rounded-2xl border border-amber-200 bg-gradient-to-br from-amber-50/70 via-white to-amber-50/30 p-4.5 flex items-center justify-between shadow-2xs hover:shadow-sm transition">
          <div>
            <span className="text-[11px] font-bold text-amber-900 uppercase tracking-wider block">
              API Key Cloud
            </span>
            <span className="text-2xl sm:text-3xl font-black text-amber-950 mt-0.5 block">{apiCount}</span>
          </div>
          <div className="w-11 h-11 rounded-2xl bg-amber-100 text-amber-900 border border-amber-200 flex items-center justify-center font-black shadow-2xs">
            <Key className="w-5 h-5" />
          </div>
        </div>

        <div className="rounded-2xl border border-emerald-200 bg-gradient-to-br from-emerald-50/70 via-white to-emerald-50/30 p-4.5 flex items-center justify-between shadow-2xs hover:shadow-sm transition">
          <div>
            <span className="text-[11px] font-bold text-emerald-900 uppercase tracking-wider block">
              Ollama Locale
            </span>
            <span className="text-2xl sm:text-3xl font-black text-emerald-950 mt-0.5 block">{localCount}</span>
          </div>
          <div className="w-11 h-11 rounded-2xl bg-emerald-100 text-emerald-900 border border-emerald-200 flex items-center justify-center font-black shadow-2xs">
            <HardDrive className="w-5 h-5" />
          </div>
        </div>

        <div className="rounded-2xl border border-purple-200 bg-gradient-to-br from-purple-50/70 via-white to-purple-50/30 p-4.5 flex items-center justify-between shadow-2xs hover:shadow-sm transition">
          <div>
            <span className="text-[11px] font-bold text-purple-900 uppercase tracking-wider block">
              Ollama Remoto
            </span>
            <span className="text-2xl sm:text-3xl font-black text-purple-950 mt-0.5 block">{remoteCount}</span>
          </div>
          <div className="w-11 h-11 rounded-2xl bg-purple-100 text-purple-900 border border-purple-200 flex items-center justify-center font-black shadow-2xs">
            <Server className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* 1. SEZIONE I DUE CERVELLI PRINCIPALI (HERO FULL-WIDTH) */}
      <section className="space-y-3.5 w-full">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-2xl bg-blue-100 text-blue-900 border border-blue-200 font-black shadow-2xs">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base sm:text-lg font-black text-slate-950 tracking-tight">
              {t('two_main_brains_title')}
            </h2>
            <p className="text-xs font-semibold text-slate-600">
              {t('two_main_brains_subtitle')}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 w-full">
          {fastConversation && (
            <TargetCard
              target={fastConversation}
              isHero
              onConfigure={onSelectTarget}
              t={t}
            />
          )}
          {reasoning && (
            <TargetCard
              target={reasoning}
              isHero
              onConfigure={onSelectTarget}
              t={t}
            />
          )}
        </div>
      </section>

      {/* 2. SEZIONE SERVIZI CRITICI: LIVE AUDIO & CEO */}
      <section className="space-y-3.5 w-full">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-2xl bg-slate-100 text-slate-800 border border-slate-200 shadow-2xs">
            <Radio className="w-5 h-5 text-indigo-600" />
          </div>
          <div>
            <h2 className="text-base sm:text-lg font-black text-slate-950 tracking-tight">
              {t('critical_services_title')}
            </h2>
            <p className="text-xs font-semibold text-slate-600">
              {t('critical_services_subtitle')}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 w-full">
          {liveAudio && (
            <TargetCard
              target={liveAudio}
              onConfigure={onSelectTarget}
              t={t}
            />
          )}
          {ceo && (
            <TargetCard
              target={ceo}
              onConfigure={onSelectTarget}
              t={t}
            />
          )}
        </div>
      </section>

      {/* 3. SEZIONE TUTTI GLI AGENTI AUTONOMI (RESPONSIVE FULL-WIDTH GRID) */}
      <section className="space-y-4 w-full">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3.5 p-4 rounded-2xl bg-white border border-slate-200/90 shadow-2xs">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-indigo-100 text-indigo-900 border border-indigo-200">
              <Users className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base sm:text-lg font-black text-slate-950 tracking-tight">
                {t('team_agents_title')}
              </h2>
              <p className="text-xs font-semibold text-slate-600">
                {t('team_agents_subtitle')}
              </p>
            </div>
          </div>

          {/* Filters & Search */}
          <div className="flex flex-wrap items-center gap-2.5">
            <div className="relative flex-1 sm:w-64">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder={t('search_agent_or_model')}
                value={filterQuery}
                onChange={(e) => setFilterQuery(e.target.value)}
                className="w-full pl-9 pr-3.5 py-1.5 text-xs font-semibold rounded-full bg-slate-50 border border-slate-300 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-100"
              />
            </div>

            <div className="flex rounded-full border border-slate-200 bg-slate-100 p-1 text-xs font-bold">
              <button
                type="button"
                onClick={() => setMethodFilter('all')}
                className={`px-3 py-1 rounded-full transition ${
                  methodFilter === 'all'
                    ? 'bg-white text-slate-950 shadow-2xs font-black'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {t('filter_all')}
              </button>
              <button
                type="button"
                onClick={() => setMethodFilter('api_key')}
                className={`px-3 py-1 rounded-full transition ${
                  methodFilter === 'api_key'
                    ? 'bg-amber-100 text-amber-950 border border-amber-300 shadow-2xs font-black'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                API
              </button>
              <button
                type="button"
                onClick={() => setMethodFilter('ollama_local')}
                className={`px-3 py-1 rounded-full transition ${
                  methodFilter === 'ollama_local'
                    ? 'bg-emerald-100 text-emerald-950 border border-emerald-300 shadow-2xs font-black'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Local
              </button>
              <button
                type="button"
                onClick={() => setMethodFilter('ollama_remote')}
                className={`px-3 py-1 rounded-full transition ${
                  methodFilter === 'ollama_remote'
                    ? 'bg-purple-100 text-purple-950 border border-purple-300 shadow-2xs font-black'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                LAN
              </button>
            </div>
          </div>
        </div>

        {/* Dynamic Grid expanding responsively across large displays */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 3xl:grid-cols-6 gap-4 w-full">
          {filteredAgents.map((agent) => (
            <TargetCard
              key={agent.id}
              target={agent}
              onConfigure={onSelectTarget}
              t={t}
            />
          ))}
        </div>
      </section>
    </div>
  );
};
