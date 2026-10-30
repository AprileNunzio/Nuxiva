import React, { FormEvent, useEffect, useState } from 'react';
import { Download, HardDrive, Trash2 } from 'lucide-react';
import { ConfirmDialog } from '../../../../shared/ui/ConfirmDialog';
import { usePolled } from '../../../../node_apps/shared/hooks/useAction';
import { bytes } from '../../core/format';
import { useBrainText, useSectionText } from '../../core/i18n';
import { deleteModel, fetchLocalModels, fetchPullProgress, pullModel } from '../../core/localModelsApi';
import { MODEL_NAME } from '../../core/parse';
import { useBrain } from '../../core/useBrainStore';
import { Badge, Button, Card, Empty, IconButton, Loading, Meter, Row, SectionHeader, fieldClass } from '../../ui/primitives';
import { CatalogCard } from './CatalogCard';

export const LocalModelsSection: React.FC = () => {
  const { t } = useSectionText('local_models');
  const base = useBrainText();
  const { run, action, version } = useBrain();
  const installed = usePolled(fetchLocalModels, 'brain_local_models_unavailable', true, 30000);
  const progress = usePolled(fetchPullProgress, 'brain_pull_unavailable', true, 3000);
  const [name, setName] = useState('');
  const [deleting, setDeleting] = useState<string | null>(null);
  const { refresh } = installed;
  useEffect(() => {
    if (version > 0) refresh();
  }, [version, refresh]);
  const pulling = progress.data;
  const pullingName = pulling && pulling.percent < 100 ? pulling.name : null;

  const pull = (model: string) => run(`pull:${model}`, 'brain_pull_failed', async () => {
    await pullModel(model);
    return true;
  });

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const clean = name.trim();
    if (MODEL_NAME.test(clean) && (await pull(clean))) setName('');
  };

  const confirmDelete = async () => {
    if (!deleting) return;
    await run(`delete:${deleting}`, 'brain_delete_failed', async () => {
      await deleteModel(deleting);
      return true;
    });
    setDeleting(null);
  };

  return (
    <>
      <SectionHeader title={t('title')} description={t('description')} />
      {pullingName && pulling && (
        <Card title={t('downloading', { name: pullingName })}>
          <Meter value={pulling.percent / 100} label={t('downloading', { name: pullingName })} />
          <p className="mt-2 text-xs text-slate-500">{t('percent', { n: Math.round(pulling.percent) })}</p>
        </Card>
      )}
      <Card title={t('installed_title', { count: installed.data?.length ?? 0 })} flush>
        {installed.data === null ? (
          <div className="px-5"><Loading label={base.t('loading')} /></div>
        ) : installed.data.length === 0 ? (
          <div className="p-4"><Empty>{t('installed_empty')}</Empty></div>
        ) : (
          installed.data.map((model) => (
            <Row
              key={model.name}
              icon={HardDrive}
              title={<>{model.name}{model.loaded && <Badge tone="success">{t('loaded')}</Badge>}</>}
              description={bytes(model.size)}
              trailing={<IconButton icon={Trash2} tone="danger" label={t('delete')} disabled={action.busy !== null} onClick={() => setDeleting(model.name)} />}
            />
          ))
        )}
        <form onSubmit={(e) => void submit(e)} className="flex flex-col gap-2 border-t border-slate-100 bg-slate-50 px-4 py-3 sm:flex-row sm:px-5">
          <label className="min-w-0 flex-1">
            <span className="sr-only">{t('pull_placeholder')}</span>
            <input value={name} maxLength={120} onChange={(e) => setName(e.target.value)} placeholder={t('pull_placeholder')} className={`${fieldClass} font-mono text-xs`} />
          </label>
          <Button type="submit" icon={Download} busy={action.busy === `pull:${name.trim()}`} disabled={action.busy !== null || !MODEL_NAME.test(name.trim())}>
            {t('pull')}
          </Button>
        </form>
      </Card>
      <CatalogCard pulling={pullingName} onPull={(model) => void pull(model)} />
      {deleting && (
        <ConfirmDialog
          title={t('delete_title')}
          body={t('delete_body', { name: deleting })}
          confirmLabel={t('delete')}
          cancelLabel={base.t('cancel')}
          pending={action.busy === `delete:${deleting}`}
          tone="danger"
          onConfirm={() => void confirmDelete()}
          onCancel={() => setDeleting(null)}
        />
      )}
    </>
  );
};
