import React, { useCallback, useEffect, useState } from 'react';
import { Cpu, Database, Layers, Plus, Radio, RefreshCw, Wrench } from 'lucide-react';
import { useWindowNodeContext } from '../../app_shell/window_manager/WindowContext';
import { createMission, fetchMissions } from './api';
import { KnowledgeGraphViewer } from './components/KnowledgeGraphViewer';
import { MissionDetail } from './components/MissionDetail';
import { RuntimeConfigPanel } from './components/RuntimeConfigPanel';
import { ToolCatalogViewer } from './components/ToolCatalogViewer';
import { inputFieldClass, primaryBtnClass, useAutonomousI18n } from './scope';
import { Mission } from './types';

export const View: React.FC = () => {
  const { t } = useAutonomousI18n();
  const { payload } = useWindowNodeContext();
  const initialMissionId =
    payload && typeof payload.missionId === 'string' ? payload.missionId : null;

  const [missions, setMissions] = useState<Mission[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(initialMissionId);
  const [activeTab, setActiveTab] = useState<'missions' | 'runtime' | 'knowledge' | 'tools' | 'new'>('missions');
  const [newGoal, setNewGoal] = useState('');
  const [newDirectives, setNewDirectives] = useState('');
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [liveSync, setLiveSync] = useState(true);

  const loadMissions = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const data = await fetchMissions();
      setMissions(data);
      setSelectedId((prev) => {
        if (prev && data.some((m) => m.id === prev)) return prev;
        if (initialMissionId && data.some((m) => m.id === initialMissionId)) return initialMissionId;
        return data[0]?.id || null;
      });
    } catch {
      return;
    } finally {
      if (!silent) setLoading(false);
    }
  }, [initialMissionId]);

  useEffect(() => {
    void loadMissions(false);
  }, [loadMissions]);

  useEffect(() => {
    if (initialMissionId) {
      setSelectedId(initialMissionId);
      setActiveTab('missions');
    }
  }, [initialMissionId]);

  useEffect(() => {
    if (!liveSync || activeTab !== 'missions') return;
    const timer = window.setInterval(() => {
      void loadMissions(true);
    }, 4000);
    return () => window.clearInterval(timer);
  }, [liveSync, activeTab, loadMissions]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!newGoal.trim()) return;
    setCreating(true);
    try {
      const dirList = newDirectives
        .split('\n')
        .map((d) => d.trim())
        .filter(Boolean);
      const created = await createMission(newGoal.trim(), dirList);
      setMissions((prev) => [created, ...prev]);
      setSelectedId(created.id);
      setNewGoal('');
      setNewDirectives('');
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
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setLiveSync((v) => !v)}
            className={`flex items-center gap-1.5 rounded-xl border px-3 py-2 text-xs font-semibold transition ${
              liveSync
                ? 'border-emerald-600/60 bg-emerald-950/40 text-emerald-300'
                : 'border-slate-700 bg-slate-900/60 text-slate-400'
            }`}
          >
            <Radio className={`h-3.5 w-3.5 ${liveSync ? 'animate-pulse text-emerald-400' : ''}`} />
            {t('live_sync_toggle')}
          </button>
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
            onClick={() => setActiveTab('knowledge')}
            className={`rounded-xl px-4 py-2 text-xs font-semibold transition ${
              activeTab === 'knowledge'
                ? 'bg-cyan-600 text-white shadow-lg shadow-cyan-600/30'
                : 'border border-slate-700 bg-slate-900/60 text-slate-300 hover:bg-slate-800'
            }`}
          >
            <Database className="mr-1.5 inline h-4 w-4" />
            {t('tab_knowledge')}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('tools')}
            className={`rounded-xl px-4 py-2 text-xs font-semibold transition ${
              activeTab === 'tools'
                ? 'bg-cyan-600 text-white shadow-lg shadow-cyan-600/30'
                : 'border border-slate-700 bg-slate-900/60 text-slate-300 hover:bg-slate-800'
            }`}
          >
            <Wrench className="mr-1.5 inline h-4 w-4" />
            {t('tab_tools')}
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

      {activeTab === 'knowledge' && <KnowledgeGraphViewer t={t} />}

      {activeTab === 'tools' && <ToolCatalogViewer />}

      {activeTab === 'new' && (
        <form
          onSubmit={(e) => void handleCreate(e)}
          className="flex max-w-2xl flex-col gap-4 rounded-2xl border border-slate-800 bg-slate-900/40 p-6"
        >
          <h2 className="text-lg font-bold text-slate-100">{t('tab_new_mission')}</h2>
          <textarea
            rows={4}
            placeholder={t('goal_placeholder')}
            value={newGoal}
            onChange={(e) => setNewGoal(e.target.value)}
            className={inputFieldClass}
          />
          <textarea
            rows={3}
            placeholder={t('directives_placeholder')}
            value={newDirectives}
            onChange={(e) => setNewDirectives(e.target.value)}
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
        <div className="grid gap-6 lg:grid-cols-[20rem_minmax(0,1fr)]">
          <aside className="flex flex-col gap-3 rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                {t('stat_active')} ({missions.length})
              </span>
              <button
                type="button"
                onClick={() => void loadMissions(false)}
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
                        ? 'border-cyan-500 bg-cyan-950/25 text-white'
                        : 'border-slate-800 bg-slate-950/40 text-slate-300 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 text-xs">
                      <span className="truncate font-semibold">{m.title}</span>
                      <span className="shrink-0 rounded bg-slate-800 px-1.5 py-0.5 text-[10px] font-mono uppercase text-cyan-400">
                        {m.status}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-slate-400">
                      <span>{m.domain}</span>
                      <span>
                        {m.progress}% · {m.artifacts?.length || 0} file
                      </span>
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
