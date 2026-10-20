import React, { useState } from 'react';
import { Binary, FlaskConical, Search, Trash2 } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { AppFrame, Btn, Empty, List, Loading, Panel, Pill, Row, Stat, StatRow, Toggle, Unreachable, inputClass } from '../shared/kit';
import { useAction, useResource } from '../shared/useResource';
import { removeAlgorithm, setEnabled, testAlgorithm } from './api';
import { AlgorithmTest, AlgorithmsOverview } from './types';

export const View: React.FC = () => {
  const { t } = useScopedI18n('core_apps/algorithms');
  const { data, error, loading, reload } = useResource<AlgorithmsOverview>('/api/skills', 20000);
  const { busy, run } = useAction(reload);
  const [filter, setFilter] = useState('');
  const [category, setCategory] = useState('');
  const [probe, setProbe] = useState<Record<string, string>>({});
  const [results, setResults] = useState<Record<string, AlgorithmTest>>({});

  if (loading && !data) {
    return <Loading label={t('loading')} />;
  }
  if (!data) {
    return <Unreachable label={t(error ? 'unreachable' : 'loading')} />;
  }

  const needle = filter.trim().toLowerCase();
  const rows = data.skills.filter(
    (item) => (!category || item.category === category) && (!needle || `${item.name} ${item.description}`.toLowerCase().includes(needle)),
  );
  const uses = data.skills.reduce((sum, item) => sum + item.stats.uses, 0);

  const test = async (key: string, fallback: string) => {
    const text = (probe[key] ?? fallback).trim();
    if (!text) {
      return;
    }
    const out = await run(() => testAlgorithm(key, text), 'algorithms_test_failed');
    if (out) {
      setResults((current) => ({ ...current, [key]: out }));
    }
  };

  return (
    <AppFrame title={t('title')} description={t('description')} onReload={reload}>
      <StatRow>
        <Stat label={t('stat_total')} value={data.skills.length} />
        <Stat label={t('stat_enabled')} value={data.skills.filter((item) => item.stats.enabled).length} tone="emerald" />
        <Stat label={t('stat_uses')} value={uses} tone="purple" />
        <Stat label={t('stat_errors')} value={data.errors.length} tone={data.errors.length ? 'rose' : 'slate'} />
      </StatRow>
      <Panel title={t('library_title')} icon={<Binary className="h-4 w-4 text-purple-300" aria-hidden="true" />}>
        <div className="mb-3 grid gap-2 sm:grid-cols-3">
          <div className="relative sm:col-span-2">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" aria-hidden="true" />
            <input className={`${inputClass} pl-9`} value={filter} onChange={(event) => setFilter(event.target.value)} placeholder={t('search')} aria-label={t('search')} />
          </div>
          <select className={inputClass} value={category} onChange={(event) => setCategory(event.target.value)} aria-label={t('category')}>
            <option value="">{t('all_categories')}</option>
            {Object.entries(data.categories).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </div>
        {rows.length === 0 ? (
          <Empty>{t('empty')}</Empty>
        ) : (
          <List>
            {rows.map((item) => {
              const example = item.examples[0] ?? '';
              const outcome = results[item.key];
              return (
                <Row
                  key={item.key}
                  actions={
                    <>
                      <Toggle checked={item.stats.enabled} disabled={busy} label={t('enabled')} onChange={(value) => void run(() => setEnabled(item.key, value), 'algorithms_toggle_failed')} />
                      {item.source !== 'system' ? (
                        <Btn tone="rose" busy={busy} onClick={() => void run(() => removeAlgorithm(item.key), 'algorithms_delete_failed')} title={t('delete')}>
                          <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                        </Btn>
                      ) : null}
                    </>
                  }
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <b>{item.name}</b>
                    <Pill tone="purple">{item.category_label}</Pill>
                    {item.source !== 'system' ? <Pill tone="cyan">{t('created_by_nuxiva')}</Pill> : null}
                  </div>
                  <p className="text-xs text-slate-400">{item.description}</p>
                  <p className="mt-1 text-[11px] text-slate-500">{t('usage', { uses: item.stats.uses, fails: item.stats.fails })}</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <input
                      className={`${inputClass} max-w-md flex-1`}
                      value={probe[item.key] ?? example}
                      onChange={(event) => setProbe((current) => ({ ...current, [item.key]: event.target.value }))}
                      aria-label={t('try_label')}
                      maxLength={500}
                    />
                    <Btn busy={busy} onClick={() => void test(item.key, example)}>
                      <FlaskConical className="h-3.5 w-3.5" aria-hidden="true" />
                      {t('try')}
                    </Btn>
                  </div>
                  {outcome ? (
                    <p className={`mt-2 text-xs ${outcome.ok ? 'text-emerald-300' : 'text-rose-300'}`}>
                      {outcome.ok ? String(outcome.result ?? '') : outcome.error} · {outcome.total_ms} ms · {outcome.matches ? t('matches') : t('no_match')}
                    </p>
                  ) : null}
                </Row>
              );
            })}
          </List>
        )}
      </Panel>
    </AppFrame>
  );
};

export default View;
