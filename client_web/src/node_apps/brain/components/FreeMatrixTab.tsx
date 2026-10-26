import React, { useEffect, useState } from 'react';
import { Loader2, RefreshCw, Save } from 'lucide-react';
import { Panel } from '../../shared/components/ModuleFrame';
import { ActionHandle, usePolled } from '../../shared/hooks/useAction';
import { FREE_POOLS, FreePool, fetchFreeMatrix, refreshFreeCatalog, saveFreeMatrix } from '../data/freeMatrixApi';
import { chipButton } from '../scope';
import { useScopedI18n } from '../../../shared/i18n/useScopedI18n';

interface Props {
  readonly action: ActionHandle;
  readonly onChanged: () => void;
}

export const FreeMatrixTab: React.FC<Props> = ({ action, onChanged }) => {
  const { t } = useScopedI18n('node_apps/brain/free_matrix');
  const matrix = usePolled(fetchFreeMatrix, 'node_brain_free_matrix_failed', true, 5000);
  const [enabled, setEnabled] = useState(false);
  const [pools, setPools] = useState<FreePool[]>(['chat', 'agent_tools', 'vision', 'deep_code', 'voice_fast']);
  const [dirty, setDirty] = useState(false);
  useEffect(() => {
    if (!matrix.data || dirty) return;
    setEnabled(matrix.data.enabled);
    setPools([...matrix.data.pools]);
  }, [dirty, matrix.data]);
  const updatePool = (pool: FreePool, selected: boolean) => {
    setPools((current) => selected ? [...new Set([...current, pool])] : current.filter((item) => item !== pool));
  };
  const save = async () => {
    const saved = await action.run('free-matrix:save', async () => {
      await saveFreeMatrix(enabled, pools);
      return fetchFreeMatrix();
    }, 'node_brain_free_matrix_failed');
    if (saved) {
      matrix.setData(saved);
      setDirty(false);
      onChanged();
    }
  };
  const refresh = async () => {
    const refreshed = await action.run('free-matrix:refresh', async () => {
      await refreshFreeCatalog();
      return true;
    }, 'node_brain_free_matrix_failed');
    if (refreshed) matrix.refresh();
  };
  const busy = action.busy !== null;

  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <Panel title={t('free_matrix_title')}>
        <p className="mb-4 text-xs text-slate-400">{t('free_matrix_hint')}</p>
        <label className="flex items-start gap-3 rounded-xl border border-slate-800 bg-slate-950/60 p-3 text-sm text-slate-200">
          <input type="checkbox" checked={enabled} onChange={(event) => { setEnabled(event.target.checked); setDirty(true); }} className="mt-0.5 accent-cyan-400" />
          <span>{t('free_matrix_enable')}</span>
        </label>
        <fieldset className="mt-4 grid gap-2 sm:grid-cols-2">
          <legend className="mb-2 text-xs font-semibold text-slate-300">{t('free_matrix_pools')}</legend>
          {FREE_POOLS.map((pool) => (
            <label key={pool} className="flex items-start gap-2 rounded-lg border border-slate-800/80 p-2 text-xs text-slate-300">
              <input type="checkbox" checked={pools.includes(pool)} onChange={(event) => { updatePool(pool, event.target.checked); setDirty(true); }} className="mt-0.5 accent-cyan-400" />
              {t(`pool_${pool}`)}
            </label>
          ))}
        </fieldset>
        <div className="mt-4 flex flex-wrap gap-2">
          <button type="button" disabled={busy} onClick={() => void save()} className={`${chipButton} border-cyan-400/50 bg-cyan-400/10 text-cyan-100`}>
            {action.busy === 'free-matrix:save' ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : <Save className="h-3.5 w-3.5" aria-hidden="true" />}
            {t('free_matrix_save')}
          </button>
          <button type="button" disabled={busy} onClick={() => void refresh()} className={`${chipButton} border-slate-700 text-slate-200`}>
            {action.busy === 'free-matrix:refresh' ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />}
            {t('free_matrix_refresh')}
          </button>
        </div>
        {matrix.data?.updatedAt ? <p className="mt-3 text-[11px] text-slate-500">{t('free_matrix_updated', { date: new Date(matrix.data.updatedAt * 1000).toLocaleString() })}</p> : null}
      </Panel>
      <Panel title={t('free_matrix_live_title')}>
        {matrix.data?.live ? (
          <div className="space-y-1 text-xs text-slate-300">
            <p>{t('free_matrix_live_route', { provider: matrix.data.live.provider, model: matrix.data.live.model })}</p>
            <p>{t('free_matrix_live_pool', { pool: matrix.data.live.pool })}</p>
            {matrix.data.live.failover ? <p className="text-amber-300">{t('free_matrix_live_failover', { model: matrix.data.live.previousModel })}</p> : null}
          </div>
        ) : <p className="text-xs text-slate-400">{t('free_matrix_live_idle')}</p>}
      </Panel>
      <Panel title={t('free_matrix_models', { count: matrix.data?.models.length ?? 0 })}>
        {matrix.data === null ? <Loader2 className="h-4 w-4 animate-spin text-cyan-300" aria-label={t('loading')} /> : matrix.data.models.length === 0 ? (
          <p className="text-xs text-slate-400">{t('free_matrix_empty')}</p>
        ) : (
          <ul className="max-h-[32rem] space-y-2 overflow-y-auto">
            {matrix.data.models.map((model) => (
              <li key={model.id} className="rounded-xl border border-slate-800/80 bg-slate-950/40 p-3">
                <p className="break-all text-sm font-semibold text-slate-100">{model.name}</p>
                <p className="mt-1 break-all font-mono text-[10px] text-slate-500">{model.id}</p>
                <p className="mt-2 text-[11px] text-cyan-200">{model.pools.map((pool) => t(`pool_${pool}`)).join(' · ') || t('free_matrix_no_pool')}</p>
                <p className="mt-1 text-[11px] text-slate-500">{t('free_matrix_context', { count: model.context })}{model.cooldownSeconds ? ` · ${t('free_matrix_cooldown', { seconds: model.cooldownSeconds })}` : ''}</p>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
};
