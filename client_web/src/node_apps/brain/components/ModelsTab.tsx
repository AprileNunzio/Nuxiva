import React, { FormEvent, useCallback, useState } from 'react';
import { Download, HardDrive, Loader2, Trash2 } from 'lucide-react';
import { ConfirmDialog } from '../../../shared/ui/ConfirmDialog';
import { Panel } from '../../shared/components/ModuleFrame';
import { ActionHandle, usePolled } from '../../shared/hooks/useAction';
import { BrainOverview, CatalogModel } from '../data/brainApi';
import { deleteModel, fetchLocalModels, fetchPullProgress, pullModel } from '../data/modelsApi';
import { MODEL_NAME } from '../data/parse';
import { bytes, chipButton, fieldClass, useBrainI18n } from '../scope';

interface ModelsTabProps {
  readonly overview: BrainOverview;
  readonly action: ActionHandle;
  readonly onChanged: () => void;
}

const FIT_TONE = { ok: 'text-emerald-300', slow: 'text-amber-200', no: 'text-rose-300' } as const;

export const ModelsTab: React.FC<ModelsTabProps> = ({ overview, action, onChanged }) => {
  const { t } = useBrainI18n();
  const [removing, setRemoving] = useState<string | null>(null);
  const [custom, setCustom] = useState('');
  const local = usePolled(fetchLocalModels, 'node_brain_models_unavailable', true, 10000);
  const progress = usePolled(fetchPullProgress, 'node_brain_pull_unavailable', true, 1500);
  const pulling = progress.data && progress.data.percent < 100 && !progress.data.status.startsWith('errore') ? progress.data : null;

  const pull = useCallback(
    async (name: string) => {
      await action.run(`pull:${name}`, () => pullModel(name), 'node_brain_pull_failed');
      progress.refresh();
    },
    [action, progress],
  );

  const fit = (model: CatalogModel) =>
    model.fit.level === 'no' ? t('fit_no') : t(`fit_${model.fit.level}`, { tps: Math.round(model.fit.tps), where: model.fit.where });

  const submitCustom = async (event: FormEvent) => {
    event.preventDefault();
    if (MODEL_NAME.test(custom.trim())) {
      await pull(custom.trim());
      setCustom('');
    }
  };

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
      <div className="flex min-w-0 flex-col gap-4">
        <Panel title={t('installed_title', { count: local.data?.length ?? 0 })}>
          {pulling && (
            <div className="mb-3 rounded-xl border border-cyan-400/40 bg-cyan-400/5 p-3" aria-live="polite">
              <p className="flex justify-between text-xs text-cyan-100">
                <span className="truncate font-mono">{pulling.name}</span>
                <span>{pulling.percent}%</span>
              </p>
              <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-slate-800">
                <div className="h-full rounded-full bg-gradient-to-r from-cyan-400 to-indigo-500 transition-[width]" style={{ width: `${pulling.percent}%` }} />
              </div>
              <p className="mt-1 truncate text-[11px] text-slate-400">{pulling.status}</p>
            </div>
          )}
          {local.data === null ? (
            <Loader2 className="h-4 w-4 animate-spin text-cyan-300" aria-label={t('loading')} />
          ) : local.data.length === 0 ? (
            <p className="text-sm text-slate-500">{t('installed_empty')}</p>
          ) : (
            <ul className="flex flex-col gap-1.5">
              {local.data.map((model) => (
                <li key={model.name} className="flex items-center gap-2 rounded-lg border border-slate-800/80 bg-slate-950/40 px-3 py-2">
                  <HardDrive className="h-4 w-4 shrink-0 text-slate-400" aria-hidden="true" />
                  <span className="min-w-0 flex-1 truncate font-mono text-xs text-slate-100">{model.name}</span>
                  {model.loaded && <span className="rounded-full border border-emerald-400/40 px-1.5 py-0.5 text-[10px] text-emerald-200">{t('loaded')}</span>}
                  <span className="shrink-0 text-[11px] text-slate-500">{bytes(model.size)}</span>
                  <button type="button" aria-label={t('delete_model')} disabled={action.busy !== null} onClick={() => setRemoving(model.name)} className="rounded p-1 text-slate-500 hover:text-rose-300 disabled:opacity-50">
                    <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
          )}
          <form onSubmit={submitCustom} className="mt-3 flex gap-2 border-t border-slate-800/80 pt-3">
            <input aria-label={t('pull_custom')} placeholder={t('pull_custom')} maxLength={120} value={custom} onChange={(event) => setCustom(event.target.value.trim())} className={`${fieldClass} min-w-0 flex-1 font-mono text-xs`} />
            <button type="submit" disabled={!MODEL_NAME.test(custom) || pulling !== null || action.busy !== null} className={`${chipButton} border-cyan-400/50 bg-cyan-400/10 text-cyan-100`}>
              <Download className="h-3.5 w-3.5" aria-hidden="true" />
              {t('pull')}
            </button>
          </form>
        </Panel>
      </div>
      <Panel title={t('catalog_title')}>
        <ul className="grid gap-2 md:grid-cols-2">
          {overview.catalog
            .filter((model) => model.sizeGb !== null)
            .map((model) => (
              <li key={model.name} className="flex flex-col gap-1 rounded-xl border border-slate-800/80 bg-slate-950/40 p-3">
                <p className="flex items-center justify-between gap-2 text-sm font-semibold text-slate-100">
                  <span className="truncate">{model.label}</span>
                  <span className="shrink-0 font-mono text-[11px] text-slate-500">{model.sizeGb} GB</span>
                </p>
                <p className="line-clamp-2 text-[11px] text-slate-400">{model.notes}</p>
                <p className={`text-[11px] ${FIT_TONE[model.fit.level]}`}>{fit(model)}</p>
                {model.licenseWarning && <p className="text-[10px] text-amber-200/80">{model.licenseWarning}</p>}
                <div className="mt-1">
                  {model.installed ? (
                    <span className="text-xs text-emerald-300">{t('installed')}</span>
                  ) : (
                    <button
                      type="button"
                      disabled={model.fit.level === 'no' || pulling !== null || action.busy !== null}
                      onClick={() => void pull(model.name)}
                      className={`${chipButton} border-cyan-400/50 bg-cyan-400/10 text-cyan-100 hover:bg-cyan-400/20`}
                    >
                      {action.busy === `pull:${model.name}` ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : <Download className="h-3.5 w-3.5" aria-hidden="true" />}
                      {t('pull')}
                    </button>
                  )}
                </div>
              </li>
            ))}
        </ul>
      </Panel>
      {removing && (
        <ConfirmDialog
          title={t('delete_model_title')}
          body={t('delete_model_body', { name: removing })}
          confirmLabel={t('delete_model')}
          cancelLabel={t('cancel')}
          pending={action.busy !== null}
          tone="danger"
          onConfirm={() =>
            void action.run(`delete:${removing}`, () => deleteModel(removing), 'node_brain_delete_failed').then(() => {
              setRemoving(null);
              local.refresh();
              onChanged();
            })
          }
          onCancel={() => setRemoving(null)}
        />
      )}
    </div>
  );
};
