import React, { useEffect, useState } from 'react';
import { RefreshCw, Save } from 'lucide-react';
import { usePolled } from '../../../../node_apps/shared/hooks/useAction';
import { FREE_POOLS, FreePool, fetchFreeMatrix, refreshFreeCatalog, saveFreeMatrix } from '../../core/freeMatrixApi';
import { useBrainText, useSectionText } from '../../core/i18n';
import { useBrain } from '../../core/useBrainStore';
import { Badge, Button, Card, Empty, Loading, Switch } from '../../ui/primitives';

export const FreeMatrixCard: React.FC = () => {
  const { t } = useSectionText('advanced');
  const base = useBrainText();
  const { run, action } = useBrain();
  const matrix = usePolled(fetchFreeMatrix, 'brain_free_matrix_failed', true, 10000);
  const [enabled, setEnabled] = useState(false);
  const [pools, setPools] = useState<FreePool[]>([...FREE_POOLS]);
  const [dirty, setDirty] = useState(false);
  useEffect(() => {
    if (!matrix.data || dirty) return;
    setEnabled(matrix.data.enabled);
    setPools([...matrix.data.pools]);
  }, [dirty, matrix.data]);

  const togglePool = (pool: FreePool, on: boolean) => {
    setPools((current) => (on ? [...new Set([...current, pool])] : current.filter((item) => item !== pool)));
    setDirty(true);
  };

  const save = async () => {
    const done = await run('free:save', 'brain_free_matrix_failed', async () => {
      await saveFreeMatrix(enabled, pools);
      return true;
    });
    if (done) {
      setDirty(false);
      matrix.refresh();
    }
  };

  const refresh = async () => {
    const done = await action.run('free:refresh', async () => {
      await refreshFreeCatalog();
      return true;
    }, 'brain_free_matrix_failed');
    if (done) matrix.refresh();
  };

  const data = matrix.data;
  return (
    <Card
      title={t('free_title')}
      description={t('free_hint')}
      actions={
        <>
          <Button compact icon={RefreshCw} busy={action.busy === 'free:refresh'} disabled={action.busy !== null} onClick={() => void refresh()}>
            {t('free_refresh')}
          </Button>
          <Button compact variant="primary" icon={Save} busy={action.busy === 'free:save'} disabled={action.busy !== null || !dirty} onClick={() => void save()}>
            {base.t('save')}
          </Button>
        </>
      }
    >
      {!data ? (
        <Loading label={base.t('loading')} />
      ) : (
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-3">
            <Switch checked={enabled} label={t('free_enable')} onChange={(v) => { setEnabled(v); setDirty(true); }} />
            <span className="text-sm text-slate-800">{t('free_enable')}</span>
          </div>
          <fieldset className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            <legend className="mb-2 text-xs font-medium text-slate-700">{t('free_pools')}</legend>
            {FREE_POOLS.map((pool) => (
              <label key={pool} className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-800">
                <input type="checkbox" checked={pools.includes(pool)} onChange={(e) => togglePool(pool, e.target.checked)} className="h-4 w-4 accent-blue-600" />
                {t(`pool_${pool}`)}
              </label>
            ))}
          </fieldset>
          <div className="rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-600" aria-live="polite">
            {data.live ? (
              <>
                {t('free_live', { provider: data.live.provider, model: data.live.model })}
                {data.live.failover && <span className="ml-1 text-amber-700">{t('free_failover', { model: data.live.previousModel })}</span>}
              </>
            ) : (
              t('free_idle')
            )}
          </div>
          <div>
            <p className="mb-2 text-xs font-medium text-slate-700">{t('free_models', { count: data.models.length })}</p>
            {data.models.length === 0 ? (
              <Empty>{t('free_empty')}</Empty>
            ) : (
              <ul className="grid max-h-80 gap-2 overflow-y-auto sm:grid-cols-2">
                {data.models.map((model) => (
                  <li key={model.id} className="rounded-lg border border-slate-200 px-3 py-2">
                    <p className="truncate text-sm font-medium text-slate-900">{model.name}</p>
                    <p className="truncate font-mono text-[11px] text-slate-500">{model.id}</p>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {model.pools.map((pool) => <Badge key={pool}>{t(`pool_${pool}`)}</Badge>)}
                      {model.cooldownSeconds > 0 && <Badge tone="warning">{t('free_cooldown', { seconds: model.cooldownSeconds })}</Badge>}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </Card>
  );
};
