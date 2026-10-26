import React, { useEffect, useState } from 'react';
import { Activity, Cpu, Layers, ListFilter, Plus, RefreshCw } from 'lucide-react';
import { createMission, fetchMissions } from './api';
import { MissionDetail } from './components/MissionDetail';
import { RuntimeConfigPanel } from './components/RuntimeConfigPanel';
import { inputFieldClass, primaryBtnClass, secondaryBtnClass, useAutonomousI18n } from './scope';
import { Mission } from './types';

export const View: React.FC = () => {
  const { t } = useAutonomousI18n();
  const [missions, setMissions] = useState<Mission[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'missions' | 'runtime' | 'new'>('missions');
  const [newGoal, setNewGoal] = useState('');
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    void loadMissions();
  }, []);

  async function loadMissions() {
    setLoading(true);
    try {
      const data = await fetchMissions();
      setMissions(data);
      if (!selectedId && data.length > 0) {
        setSelectedId(data[0].id);
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!newGoal.trim()) return;
    setCreating(true);
    try {
      const created = await createMission(newGoal.trim());
      setMissions([created, ...missions]);
      setSelectedId(created.id);
      setNewGoal('');
      setActiveTab('missions');
    } finally {
      setCreating(false);
    }
  }

  const selectedMission = missions.find((m) => m.id === selectedId) || missions[0] || null;

  return (
    <div className="flex h-full w-full flex-col gap-6 overflow-y-auto p-4 md:p-6">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-black tracking-tight text-white md:text-3xl">{t('title')}</h1>
          <p className="mt-1 text-xs text-slate-400">{t('description')}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setActiveTab('missions')}
            className={`rounded-xl px-4 py-2 text-xs font-semibold transition ${
              activeTab === 'missions'
                ? 'bg-cyan-600 text-white shadow-lg shadow-cyan-600/30'
                : 'border border-slate-700 bg-slate-900/60 text-slate-300 hover:bg-slate-800'
            }`}
          >
            <Layers className="mr-1.5 inline h-4 w-4" />
            {t('tab_missions')}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('runtime')}
            className={`rounded-xl px-4 py-2 text-xs font-semibold transition ${
              activeTab === 'runtime'
                ? 'bg-cyan-600 text-white shadow-lg shadow-cyan-600/30'
                : 'border border-slate-700 bg-slate-900/60 text-slate-300 hover:bg-slate-800'
            }`}
          >
            <Cpu className="mr-1.5 inline h-4 w-4" />
            {t('tab_runtime')}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('new')}
            className={`rounded-xl px-4 py-2 text-xs font-semibold transition ${
              activeTab === 'new'
                ? 'bg-cyan-600 text-white shadow-lg shadow-cyan-600/30'
                : 'border border-slate-700 bg-slate-900/60 text-slate-300 hover:bg-slate-800'
            }`}
          >
            <Plus className="mr-1.5 inline h-4 w-4" />
            {t('tab_new_mission')}
          </button>
        </div>
      </div>

      {activeTab === 'runtime' && <RuntimeConfigPanel />}

      {activeTab === 'new' && (
        <form onSubmit={(e) => void handleCreate(e)} className="flex max-w-2xl flex-col gap-4 rounded-2xl border border-slate-800 bg-slate-900/40 p-6">
          <h2 className="text-lg font-bold text-slate-100">{t('tab_new_mission')}</h2>
          <textarea
            rows={4}
            placeholder={t('goal_placeholder')}
            value={newGoal}
            onChange={(e) => setNewGoal(e.target.value)}
            className={inputFieldClass}
          />
          <div className="flex justify-end">
            <button type="submit" disabled={creating || !newGoal.trim()} className={primaryBtnClass}>
              {t('start_mission_btn')}
            </button>
          </div>
        </form>
      )}

      {activeTab === 'missions' && (
        <div className="grid gap-6 lg:grid-cols-[22rem_minmax(0,1fr)]">
          <aside className="flex flex-col gap-3 rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                {t('stat_active')} ({missions.length})
              </span>
              <button
                type="button"
                onClick={() => void loadMissions()}
                disabled={loading}
                className="text-slate-400 hover:text-white"
              >
                <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              </button>
            </div>
            <div className="flex flex-col gap-2 overflow-y-auto">
              {missions.length === 0 ? (
                <div className="p-4 text-center text-xs text-slate-500">{t('empty_missions')}</div>
              ) : (
                missions.map((m) => (
                  <button
                    key={m.id}
                    type="button"
                    onClick={() => setSelectedId(m.id)}
                    className={`flex flex-col gap-1.5 rounded-xl border p-3 text-left transition ${
                      selectedId === m.id
                        ? 'border-cyan-500 bg-cyan-950/20 text-white'
                        : 'border-slate-800 bg-slate-950/40 text-slate-300 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold">{m.title}</span>
                      <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] font-mono uppercase text-cyan-400">
                        {m.status}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-slate-400">
                      <span>{m.domain}</span>
                      <span>{m.progress}%</span>
                    </div>
                  </button>
                ))
              )}
            </div>
          </aside>
          <main className="min-w-0">
            {selectedMission ? (
              <MissionDetail
                mission={selectedMission}
                onUpdate={(upd) =>
                  setMissions((prev) => prev.map((m) => (m.id === upd.id ? upd : m)))
                }
              />
            ) : null}
          </main>
        </div>
      )}
    </div>
  );
};
