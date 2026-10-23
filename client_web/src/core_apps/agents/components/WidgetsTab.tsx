import React, { useMemo, useState } from 'react';
import { Trash2, Users } from 'lucide-react';
import { Agent, Person, WidgetInfo, deleteWidget, updateWidget } from '../data/teamApi';
import { TeamHandle } from '../hooks/useTeam';
import { chipClass, fieldClass, useAgentsI18n } from '../scope';

interface WidgetsTabProps {
  readonly agent: Agent;
  readonly agents: readonly Agent[];
  readonly widgets: readonly WidgetInfo[];
  readonly people: readonly Person[];
  readonly handle: TeamHandle;
}

export const WidgetsTab: React.FC<WidgetsTabProps> = ({ agent, agents, widgets, people, handle }) => {
  const { t } = useAgentsI18n();
  const [adding, setAdding] = useState('');
  const mine = useMemo(() => widgets.filter((w) => w.agent === agent.id), [widgets, agent.id]);
  const others = useMemo(() => widgets.filter((w) => w.agent !== agent.id), [widgets, agent.id]);
  const busy = handle.busy !== null;

  const togglePerson = (widget: WidgetInfo, slug: string) => {
    const next = widget.people.includes(slug) ? widget.people.filter((p) => p !== slug) : [...widget.people, slug];
    void handle.run(`widget:${widget.id}`, () => updateWidget(widget.id, { people: next }), 'team_widget_failed');
  };

  return (
    <div className="flex flex-col gap-3">
      {mine.length === 0 && <p className="text-sm text-slate-500">{t('widgets_empty')}</p>}
      <ul className="flex flex-col gap-2">
        {mine.map((widget) => (
          <li key={widget.id} className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5">
            <div className="flex items-center gap-2">
              <span className="text-lg" aria-hidden="true">{widget.icon || '▣'}</span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm text-slate-900">{widget.name}</span>
                <span className="block font-mono text-[10px] text-slate-500">
                  {widget.id}
                  {widget.personal ? ` · ${t('personal')}` : ''}
                  {!widget.enabled ? ` · ${t('widget_off')}` : ''}
                </span>
              </span>
              <select
                disabled={busy}
                value={widget.agent}
                aria-label={t('owner')}
                onChange={(event) =>
                  void handle.run(`widget:${widget.id}`, () => updateWidget(widget.id, { agent: event.target.value === widget.defaultAgent ? '' : event.target.value }), 'team_widget_failed')
                }
                className={`${fieldClass} max-w-[45%] py-1 text-xs`}
              >
                {agents.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
              {widget.source === 'ai' && (
                <button
                  type="button"
                  disabled={busy}
                  aria-label={t('delete_widget')}
                  onClick={() => void handle.run(`widget:${widget.id}`, () => deleteWidget(widget.id), 'team_widget_failed')}
                  className="rounded-lg p-1.5 text-slate-500 transition hover:text-rose-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-300"
                >
                  <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                </button>
              )}
            </div>
            <div className="mt-2">
              <p className="mb-1 flex items-center gap-1.5 text-[11px] text-slate-600">
                <Users className="h-3.5 w-3.5" aria-hidden="true" />
                {widget.people.length ? t('people_only') : t('people_all')}
              </p>
              <div className="flex flex-wrap gap-1.5">
                {people.map((person) => (
                  <button
                    key={person.slug}
                    type="button"
                    aria-pressed={widget.people.includes(person.slug)}
                    disabled={busy}
                    onClick={() => togglePerson(widget, person.slug)}
                    className={`${chipClass} ${widget.people.includes(person.slug) ? 'border-emerald-300 bg-emerald-50 text-emerald-900' : 'border-slate-300 text-slate-600'}`}
                  >
                    {person.name}
                  </button>
                ))}
                {people.length === 0 && <span className="text-[11px] text-slate-500">{t('no_people')}</span>}
              </div>
            </div>
          </li>
        ))}
      </ul>
      <div className="flex gap-2 border-t border-slate-200 pt-3">
        <select value={adding} onChange={(event) => setAdding(event.target.value)} aria-label={t('assign_widget')} className={`${fieldClass} min-w-0 flex-1`}>
          <option value="">{t('assign_widget')}</option>
          {others.map((w) => (
            <option key={w.id} value={w.id}>
              {w.icon} {w.name}
            </option>
          ))}
        </select>
        <button
          type="button"
          disabled={busy || !adding}
          onClick={() => void handle.run('assign', () => updateWidget(adding, { agent: agent.id }), 'team_widget_failed').then((ok) => ok && setAdding(''))}
          className={`${chipClass} border-cyan-300 bg-cyan-50 px-3 text-cyan-900`}
        >
          {t('assign')}
        </button>
      </div>
    </div>
  );
};
