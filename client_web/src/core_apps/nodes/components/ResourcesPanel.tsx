import React from 'react';
import { Cpu, MemoryStick, ShieldCheck } from 'lucide-react';
import { useScopedI18n } from '../../../shared/i18n/useScopedI18n';
import { formatBytes } from '../../shared/kit';
import { useResource } from '../../shared/useResource';
import { RESOURCES_URL } from '../api';
import { ResourceLevel, ResourceSnapshot } from '../types';

const LEVEL_INK: Record<ResourceLevel, string> = {
  calm: 'text-emerald-600 dark:text-emerald-400',
  elevated: 'text-amber-600 dark:text-amber-400',
  high: 'text-orange-600 dark:text-orange-400',
  critical: 'text-rose-600 dark:text-rose-400',
};

const SAFE = /^[a-z0-9_.:-]{1,64}$/;

const Meter: React.FC<{ readonly value: number; readonly over?: boolean }> = ({ value, over = false }) => (
  <div className="h-1.5 w-full overflow-hidden rounded-full bg-on-surface/10" role="presentation">
    <div
      className={`h-full rounded-full ${over ? 'bg-rose-500' : 'bg-cyan-500'}`}
      style={{ width: `${Math.max(2, Math.min(100, value))}%` }}
    />
  </div>
);

export const ResourcesPanel: React.FC = () => {
  const { t } = useScopedI18n('core_apps/nodes');
  const { data, error } = useResource<ResourceSnapshot>(RESOURCES_URL, 5000);
  const state = data?.state;

  if (error && !state) {
    return <p className="text-sm text-on-surface-variant">{t('res_unreachable')}</p>;
  }
  if (!state || !state.level || !state.system) {
    return <p className="text-sm text-on-surface-variant">{t('res_waiting')}</p>;
  }

  const budgets = new Map((state.budgets ?? []).map((b) => [b.id, b]));
  const components = [...(state.components ?? [])].filter((c) => SAFE.test(c.id)).sort((a, b) => b.rss - a.rss).slice(0, 12);
  const actions = (data?.log ?? []).filter((a) => SAFE.test(a.id)).slice(-6).reverse();
  const total = Math.max(1, state.system.mem_total);

  return (
    <section className="flex flex-col gap-5" aria-label={t('res_title')}>
      <header className="flex flex-wrap items-end gap-x-8 gap-y-2">
        <div>
          <div className="text-[10px] font-semibold uppercase tracking-widest text-on-surface-variant">{t('res_level')}</div>
          <div className={`text-2xl font-bold ${LEVEL_INK[state.level]}`}>{t(`res_level_${state.level}`)}</div>
        </div>
        <div className="flex items-center gap-2 text-sm text-on-surface">
          <MemoryStick className="h-4 w-4" aria-hidden="true" />
          <span>{t('res_ram', { used: formatBytes(state.system.mem_total - state.system.mem_available), total: formatBytes(total) })}</span>
        </div>
        <div className="flex items-center gap-2 text-sm text-on-surface">
          <Cpu className="h-4 w-4" aria-hidden="true" />
          <span>{t('res_cpu_gpu', { cpu: Math.round(state.system.cpu_percent), gpu: Math.round(state.system.gpu_percent) })}</span>
        </div>
        <div className="text-sm text-on-surface-variant">{t('res_cores', { count: state.system.cores })}</div>
      </header>
      <p className="max-w-3xl text-sm text-on-surface-variant">{t(`res_hint_${state.level}`)}</p>
      <ul className="flex flex-col gap-3">
        {components.map((c) => {
          const budget = budgets.get(c.id);
          return (
            <li key={c.id} className="flex flex-col gap-1">
              <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
                <span className="flex items-center gap-2 font-medium text-on-surface">
                  {c.class === 'protected' && <ShieldCheck className="h-4 w-4 text-emerald-500" aria-label={t('res_protected')} />}
                  {c.id}
                  <span className="text-xs text-on-surface-variant">{t(`res_kind_${c.kind}`)}</span>
                </span>
                <span className="font-mono text-xs text-on-surface-variant">
                  {formatBytes(c.rss)}
                  {budget ? ` / ${formatBytes(budget.budget)}` : ''}
                </span>
              </div>
              <Meter value={budget && budget.budget > 0 ? (c.rss / budget.budget) * 100 : (c.rss / total) * 100} over={budget?.over} />
            </li>
          );
        })}
      </ul>
      <div>
        <h3 className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-on-surface-variant">{t('res_actions')}</h3>
        {actions.length === 0 ? (
          <p className="text-sm text-on-surface-variant">{t('res_no_actions')}</p>
        ) : (
          <ul className="flex flex-col gap-1 text-sm text-on-surface">
            {actions.map((a) => (
              <li key={`${a.at}-${a.id}-${a.action}`}>
                {t('res_action_line', { action: t(`res_action_${a.action}`), id: a.id, reason: t(`res_reason_${a.reason}`), size: formatBytes(a.reclaim) })}
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
};
