import React, { useMemo, useState } from 'react';
import { Download } from 'lucide-react';
import { useBrainText, useSectionText } from '../../core/i18n';
import { useBrain } from '../../core/useBrainStore';
import { CatalogModel } from '../../core/types';
import { Badge, Button, Card, Empty, FLUID } from '../../ui/primitives';

const FIT_TONE = { ok: 'success', slow: 'warning', no: 'danger' } as const;

export const CatalogCard: React.FC<{ readonly pulling: string | null; readonly onPull: (name: string) => void }> = ({ pulling, onPull }) => {
  const { t } = useSectionText('local_models');
  const base = useBrainText();
  const { overview, action } = useBrain();
  const [category, setCategory] = useState('all');
  const catalog: readonly CatalogModel[] = overview?.catalog ?? [];
  const categories = useMemo(() => ['all', ...new Set(catalog.map((m) => m.category))], [catalog]);
  const visible = catalog.filter((m) => category === 'all' || m.category === category);

  return (
    <Card title={t('catalog_title')} description={t('catalog_hint')} flush>
      <div className="flex gap-1 overflow-x-auto border-b border-slate-100 px-4 py-2 sm:px-5" role="tablist" aria-label={t('catalog_title')}>
        {categories.map((id) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={category === id}
            onClick={() => setCategory(id)}
            className={`shrink-0 rounded-full px-3 py-1 text-xs font-medium transition ${category === id ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'}`}
          >
            {t(`category_${id}`)}
          </button>
        ))}
      </div>
      {visible.length === 0 ? (
        <div className="p-4"><Empty>{base.t('none_available')}</Empty></div>
      ) : (
        <ul className={`grid gap-px bg-slate-100 ${FLUID.md}`}>
          {visible.map((model) => (
            <li key={model.name} className="flex flex-col gap-2 bg-white px-4 py-3 sm:px-5">
              <div className="flex items-start gap-2">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-slate-900">{model.label}</p>
                  <p className="truncate font-mono text-[11px] text-slate-500">{model.name}{model.sizeGb ? ` · ${model.sizeGb} GB` : ''}</p>
                </div>
                {model.installed ? <Badge tone="success">{t('installed')}</Badge> : null}
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={FIT_TONE[model.fit.level]}>{t(`fit_${model.fit.level}`, { tps: model.fit.tps })}</Badge>
                {model.restricted && <Badge tone="warning">{t('license_restricted')}</Badge>}
                {!model.installed && model.fit.level !== 'no' && (
                  <Button compact icon={Download} className="ml-auto" busy={pulling === model.name} disabled={action.busy !== null || pulling !== null} onClick={() => onPull(model.name)}>
                    {t('pull')}
                  </Button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
};
