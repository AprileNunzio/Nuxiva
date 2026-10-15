import React, { FormEvent, useState } from 'react';
import { Cpu, Loader2, Route } from 'lucide-react';
import { Panel } from '../../shared/components/ModuleFrame';
import { ActionHandle } from '../../shared/hooks/useAction';
import { BrainOverview, ROUTING, RouteResult, saveRouting, testRoute } from '../data/brainApi';
import { BrainRef } from '../data/parse';
import { fieldClass, useBrainI18n } from '../scope';
import { RoleCard } from './RoleCard';

interface RolesTabProps {
  readonly overview: BrainOverview;
  readonly pool: readonly BrainRef[];
  readonly action: ActionHandle;
  readonly onSaved: (overview: BrainOverview) => void;
}

export const RolesTab: React.FC<RolesTabProps> = ({ overview, pool, action, onSaved }) => {
  const { t } = useBrainI18n();
  const [text, setText] = useState('');
  const [result, setResult] = useState<RouteResult | null>(null);
  const hw = overview.hardware;

  const probe = async (event: FormEvent) => {
    event.preventDefault();
    const outcome = await action.run('route', () => testRoute(text), 'node_brain_route_failed');
    if (outcome) {
      setResult(outcome);
    }
  };

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
      <Panel title={t('roles_title')}>
        <ul className="grid gap-3 lg:grid-cols-2">
          {overview.roles.map((role) => (
            <RoleCard key={role.id} role={role} pool={pool} action={action} onSaved={onSaved} />
          ))}
        </ul>
      </Panel>
      <div className="flex min-w-0 flex-col gap-4">
        <Panel title={t('machine_title')}>
          <div className="flex items-center gap-3">
            <Cpu className="h-5 w-5 text-cyan-200" aria-hidden="true" />
            <p className="text-sm text-slate-200">
              {t('machine_ram', { ram: hw.ramGb.toFixed(0) })}
              {hw.vramGb > 0 ? ` · ${t('machine_vram', { vram: hw.vramGb.toFixed(0) })}` : ` · ${t('machine_no_gpu')}`}
            </p>
          </div>
          {hw.gpu && <p className="mt-1 truncate pl-8 text-xs text-slate-500">{hw.gpu}</p>}
          {overview.last && (
            <p className="mt-3 text-xs text-slate-400">
              {t('last_used', { model: overview.last.ref.model, ms: Math.round(overview.last.ms) })}
            </p>
          )}
        </Panel>
        <Panel title={t('routing_title')}>
          <p className="mb-2 text-xs text-slate-500">{t('routing_hint')}</p>
          <div className="grid gap-2" role="radiogroup" aria-label={t('routing_title')}>
            {ROUTING.map((mode) => (
              <button
                key={mode}
                type="button"
                role="radio"
                aria-checked={overview.routing === mode}
                disabled={action.busy !== null}
                onClick={() => void action.run('routing', () => saveRouting(mode), 'node_brain_role_failed').then((next) => next && onSaved(next))}
                className={`rounded-xl border px-3 py-2 text-left transition focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${
                  overview.routing === mode ? 'border-cyan-400/60 bg-cyan-400/10' : 'border-slate-800/80 bg-slate-950/40 hover:border-slate-600'
                }`}
              >
                <span className="block text-sm text-slate-100">{t(`routing_${mode}`)}</span>
                <span className="block text-[11px] text-slate-500">{t(`routing_${mode}_hint`)}</span>
              </button>
            ))}
          </div>
        </Panel>
        <Panel title={t('route_title')}>
          <form onSubmit={probe} className="flex flex-col gap-2">
            <textarea rows={2} maxLength={2000} value={text} placeholder={t('route_placeholder')} onChange={(event) => setText(event.target.value)} className={`${fieldClass} resize-none`} />
            <button
              type="submit"
              disabled={!text.trim() || action.busy !== null}
              className="flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-400 to-indigo-500 px-4 py-2 text-sm font-bold text-slate-950 transition hover:brightness-110 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-200"
            >
              {action.busy === 'route' ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Route className="h-4 w-4" aria-hidden="true" />}
              {t('route_submit')}
            </button>
          </form>
          {result && (
            <div className="mt-3 rounded-xl border border-slate-800/80 bg-slate-950/40 p-3 text-xs">
              <p className="text-slate-200">{t('route_kind', { kind: t(`role_${result.kind}`), reason: result.reason })}</p>
              <ol className="mt-2 list-decimal pl-4 font-mono text-cyan-100">
                {result.models.map((m) => (
                  <li key={m} className="truncate">{m}</li>
                ))}
              </ol>
              {result.skipped.length > 0 && (
                <ul className="mt-2 text-slate-500">
                  {result.skipped.map((s) => (
                    <li key={s.ref} className="truncate">
                      {s.ref} — {s.why}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
};
