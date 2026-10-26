import React, { useEffect, useState } from 'react';
import { Cpu, Plus, Server, Trash2 } from 'lucide-react';
import { deleteAgentProfile, fetchAgentProfiles, saveAgentProfile } from '../api';
import { inputFieldClass, primaryBtnClass, secondaryBtnClass, useAutonomousI18n } from '../scope';
import { AgentInferenceProfile } from '../types';

export const AgentInferenceGrid: React.FC = () => {
  const { t } = useAutonomousI18n();
  const [profiles, setProfiles] = useState<AgentInferenceProfile[]>([]);
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState<AgentInferenceProfile>({
    agent_id: '',
    label: '',
    provider: 'auto_fallback',
    endpoint: 'http://127.0.0.1:11434',
    model: 'default',
    temperature: 0.2,
    timeout_seconds: 45,
  });

  useEffect(() => {
    void load();
  }, []);

  async function load() {
    setLoading(true);
    try {
      const list = await fetchAgentProfiles();
      setProfiles(list);
    } finally {
      setLoading(false);
    }
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!editing.agent_id.trim()) return;
    try {
      const saved = await saveAgentProfile(editing);
      setProfiles((prev) => {
        const idx = prev.findIndex((p) => p.agent_id === saved.agent_id);
        if (idx >= 0) {
          const next = [...prev];
          next[idx] = saved;
          return next;
        }
        return [...prev, saved];
      });
      setEditing({
        agent_id: '',
        label: '',
        provider: 'auto_fallback',
        endpoint: 'http://127.0.0.1:11434',
        model: 'default',
        temperature: 0.2,
        timeout_seconds: 45,
      });
    } catch {}
  }

  async function handleDelete(agentId: string) {
    try {
      await deleteAgentProfile(agentId);
      setProfiles((prev) => prev.filter((p) => p.agent_id !== agentId));
    } catch {}
  }

  return (
    <div className="flex flex-col gap-5 rounded-2xl border border-slate-800 bg-slate-900/40 p-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Server className="h-5 w-5 text-indigo-400" />
          <h3 className="text-base font-semibold text-slate-100">
            {t('agent_inference_routing_title')}
          </h3>
        </div>
        <span className="text-xs text-slate-400">
          {t('agent_profiles_count', { count: profiles.length })}
        </span>
      </div>

      <p className="text-xs text-slate-400">
        {t('agent_inference_routing_desc')}
      </p>

      {profiles.length > 0 ? (
        <div className="grid gap-3 sm:grid-cols-2">
          {profiles.map((p) => (
            <div
              key={p.agent_id}
              className="flex flex-col justify-between rounded-xl border border-slate-800 bg-slate-950/60 p-4"
            >
              <div>
                <div className="flex items-center justify-between">
                  <span className="font-mono text-sm font-semibold text-cyan-300">{p.agent_id}</span>
                  <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] uppercase tracking-wide text-slate-300">
                    {p.provider}
                  </span>
                </div>
                {p.label && <p className="mt-1 text-xs text-slate-400">{p.label}</p>}
                <div className="mt-3 flex flex-col gap-1 text-[11px] text-slate-400">
                  <div>
                    <span className="text-slate-500">{t('agent_model')}:</span>{' '}
                    <span className="font-mono text-slate-200">{p.model}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">{t('agent_endpoint')}:</span>{' '}
                    <span className="font-mono text-slate-200">{p.endpoint}</span>
                  </div>
                </div>
              </div>
              <div className="mt-3 flex justify-end gap-2 border-t border-slate-850 pt-2">
                <button
                  type="button"
                  onClick={() => setEditing(p)}
                  className="text-xs text-cyan-400 hover:underline"
                >
                  {t('action_edit')}
                </button>
                <button
                  type="button"
                  onClick={() => void handleDelete(p.agent_id)}
                  className="text-xs text-rose-400 hover:underline"
                >
                  <Trash2 className="inline h-3 w-3" />
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="rounded-xl border border-dashed border-slate-800 p-4 text-center text-xs text-slate-500">
          {t('no_agent_overrides')}
        </div>
      )}

      <form onSubmit={(e) => void handleSave(e)} className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-950/30 p-4">
        <div className="font-semibold text-slate-300 text-xs uppercase tracking-wider">
          {editing.agent_id ? t('edit_agent_profile') : t('new_agent_profile')}
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-[11px] uppercase tracking-wider text-slate-400">
              {t('agent_id')}
            </label>
            <input
              type="text"
              placeholder="e.g. qa_checker, backend_coder"
              value={editing.agent_id}
              onChange={(e) => setEditing({ ...editing, agent_id: e.target.value })}
              className={inputFieldClass}
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-[11px] uppercase tracking-wider text-slate-400">
              {t('agent_label')}
            </label>
            <input
              type="text"
              placeholder="e.g. Specialista Qualità QA"
              value={editing.label}
              onChange={(e) => setEditing({ ...editing, label: e.target.value })}
              className={inputFieldClass}
            />
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <div>
            <label className="mb-1 block text-[11px] uppercase tracking-wider text-slate-400">
              {t('agent_provider')}
            </label>
            <select
              value={editing.provider}
              onChange={(e) => setEditing({ ...editing, provider: e.target.value as AgentInferenceProfile['provider'] })}
              className={inputFieldClass}
            >
              <option value="auto_fallback">{t('runtime_mode_auto')}</option>
              <option value="ollama">{t('runtime_mode_ollama')}</option>
              <option value="cloud">{t('runtime_mode_cloud')}</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-[11px] uppercase tracking-wider text-slate-400">
              {t('agent_endpoint')}
            </label>
            <input
              type="text"
              value={editing.endpoint}
              onChange={(e) => setEditing({ ...editing, endpoint: e.target.value })}
              className={inputFieldClass}
            />
          </div>
          <div>
            <label className="mb-1 block text-[11px] uppercase tracking-wider text-slate-400">
              {t('agent_model')}
            </label>
            <input
              type="text"
              placeholder="e.g. gemma4, ministral, gemini"
              value={editing.model}
              onChange={(e) => setEditing({ ...editing, model: e.target.value })}
              className={inputFieldClass}
            />
          </div>
        </div>

        <div className="mt-2 flex justify-end">
          <button type="submit" className={primaryBtnClass}>
            <Plus className="h-4 w-4" />
            {editing.agent_id ? t('save_agent_profile') : t('add_agent_profile')}
          </button>
        </div>
      </form>
    </div>
  );
};
