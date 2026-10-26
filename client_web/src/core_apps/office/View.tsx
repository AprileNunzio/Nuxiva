import React, { FormEvent, useState } from 'react';
import { Download, Eye, FilePlus } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { AppFrame, Btn, Empty, List, Loading, Panel, Pill, Row, Stat, StatRow, Unreachable, formatTime, inputClass } from '../shared/kit';
import { useAction, useResource } from '../shared/useResource';
import { createDocument, fileUrl, previewUrl } from './api';
import { DocumentsOverview } from './types';

export const View: React.FC = () => {
  const { t, lang } = useScopedI18n('core_apps/office');
  const { data, error, loading, reload } = useResource<DocumentsOverview>('/api/documents', 6000);
  const { busy, run } = useAction(reload);
  const [request, setRequest] = useState('');

  if (loading && !data) {
    return <Loading label={t('loading')} />;
  }
  if (!data) {
    return <Unreachable label={t(error ? 'unreachable' : 'loading')} />;
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (request.trim().length < 8) {
      return;
    }
    if ((await run(() => createDocument(request.trim()), 'office_create_failed')) !== null) {
      setRequest('');
    }
  };

  return (
    <AppFrame title={t('title')} description={t('description')} onReload={reload}>
      <StatRow>
        <Stat label={t('stat_documents')} value={data.items.length} />
        <Stat label={t('stat_engine')} value={data.office ? t('engine_ready') : t('engine_missing')} tone={data.office ? 'emerald' : 'amber'} />
        <Stat label={t('stat_recipes')} value={data.recipes.length} tone="purple" />
      </StatRow>
      <Panel title={t('create_title')} icon={<FilePlus className="h-4 w-4 text-cyan-700" aria-hidden="true" />}>
        <form onSubmit={(event) => void submit(event)} className="flex flex-col gap-2 sm:flex-row">
          <textarea className={`${inputClass} min-h-20 flex-1`} value={request} maxLength={600} placeholder={t('create_placeholder')} onChange={(event) => setRequest(event.target.value)} />
          <Btn type="submit" busy={busy} disabled={request.trim().length < 8}>
            {t('create')}
          </Btn>
        </form>
        <p className="mt-2 break-all text-xs text-slate-500">{data.root}</p>
      </Panel>
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title={t('documents_title')}>
          {data.items.length === 0 ? (
            <Empty>{t('documents_empty')}</Empty>
          ) : (
            <List>
              {data.items.map((item) => (
                <Row
                  key={item.id}
                  actions={
                    <>
                      {item.preview ? (
                        <a className="rounded-xl border border-slate-300 p-2 text-slate-700 hover:border-cyan-500" href={previewUrl(item.id)} target="_blank" rel="noopener noreferrer" aria-label={t('preview')}>
                          <Eye className="h-3.5 w-3.5" aria-hidden="true" />
                        </a>
                      ) : null}
                      {item.files.map((file, index) => (
                        <a key={file} className="rounded-xl border border-slate-300 p-2 text-slate-700 hover:border-emerald-500" href={fileUrl(item.id, index)} download aria-label={`${t('download')} ${file.split('/').pop()}`} title={file.split('/').pop()}>
                          <Download className="h-3.5 w-3.5" aria-hidden="true" />
                        </a>
                      ))}
                    </>
                  }
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <b className="text-sm">{item.title}</b>
                    <Pill tone="cyan">{item.kind}</Pill>
                  </div>
                  <p className="text-xs text-slate-600">{item.summary}</p>
                  <p className="text-xs text-slate-500">{formatTime(item.created, lang)}{item.seconds ? ` · ${item.seconds} s` : ''}</p>
                </Row>
              ))}
            </List>
          )}
        </Panel>
        <Panel title={t('recipes_title')}>
          {data.recipes.length === 0 ? (
            <Empty>{t('recipes_empty')}</Empty>
          ) : (
            <List>
              {data.recipes.map((recipe) => (
                <Row key={recipe.conversion}>
                  <b className="text-sm">{recipe.conversion}</b>
                  <p className="text-xs text-slate-600">{recipe.steps}</p>
                  <p className="text-xs text-slate-500">{t('recipe_uses', { count: recipe.uses })}{recipe.avg_s ? ` · ${recipe.avg_s.toFixed(1)} s` : ''}</p>
                </Row>
              ))}
            </List>
          )}
        </Panel>
      </div>
    </AppFrame>
  );
};

export default View;
