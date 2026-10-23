import React, { useEffect, useState } from 'react';
import { Loader2, Save } from 'lucide-react';
import { Agent, saveAgentSettings } from '../data/teamApi';
import { TeamHandle } from '../hooks/useTeam';
import { fieldClass, primaryClass, useAgentsI18n } from '../scope';

export const SettingsTab: React.FC<{ readonly agent: Agent; readonly handle: TeamHandle }> = ({ agent, handle }) => {
  const { t } = useAgentsI18n();
  const [draft, setDraft] = useState<Record<string, string>>({});

  useEffect(() => {
    setDraft(Object.fromEntries(agent.settings.map((s) => [s.key, s.value])));
  }, [agent.id, agent.settings]);

  if (agent.settings.length === 0) {
    return <p className="text-sm text-slate-500">{t('settings_empty')}</p>;
  }

  const changed = Object.fromEntries(agent.settings.filter((s) => (draft[s.key] ?? '') !== s.value).map((s) => [s.key, (draft[s.key] ?? '').trim()]));
  const set = (key: string, value: string) => setDraft((current) => ({ ...current, [key]: value }));

  return (
    <div className="flex flex-col gap-3">
      {agent.settings.map((s) => {
        const id = `setting-${agent.id}-${s.key}`;
        const value = draft[s.key] ?? '';
        return (
          <div key={s.key} className="flex flex-col gap-1.5 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5">
            <label htmlFor={id} className="text-sm text-slate-900">
              {s.label}
              <span className="ml-2 font-mono text-[10px] text-slate-500">{s.key}</span>
            </label>
            {s.type === 'bool' ? (
              <input id={id} type="checkbox" role="switch" checked={!['0', 'false', 'off', ''].includes(value.toLowerCase())} onChange={(event) => set(s.key, event.target.checked ? '1' : '0')} className="h-5 w-9 accent-cyan-400" />
            ) : s.type === 'select' && s.options.length > 0 ? (
              <select id={id} value={value} onChange={(event) => set(s.key, event.target.value)} className={fieldClass}>
                {!s.options.includes(value) && <option value={value}>{value || '—'}</option>}
                {s.options.map((o) => (
                  <option key={o} value={o}>
                    {o}
                  </option>
                ))}
              </select>
            ) : (
              <input
                id={id}
                type={s.type === 'secret' ? 'password' : s.type === 'number' ? 'number' : s.type === 'color' ? 'color' : 'text'}
                autoComplete="off"
                maxLength={500}
                value={value}
                onChange={(event) => set(s.key, event.target.value)}
                className={fieldClass}
              />
            )}
          </div>
        );
      })}
      <button
        type="button"
        disabled={handle.busy !== null || Object.keys(changed).length === 0}
        onClick={() => void handle.run('settings', () => saveAgentSettings(agent.id, changed), 'team_settings_failed')}
        className={primaryClass}
      >
        {handle.busy === 'settings' ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Save className="h-4 w-4" aria-hidden="true" />}
        {t('save_settings')}
      </button>
    </div>
  );
};
