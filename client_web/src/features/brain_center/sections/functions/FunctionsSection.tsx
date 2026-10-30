import React, { useEffect, useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import { usePolled } from '../../../../node_apps/shared/hooks/useAction';
import { matches } from '../../core/format';
import { fetchFunctions } from '../../core/functionsApi';
import { useBrainText, useSectionText } from '../../core/i18n';
import { useBrain } from '../../core/useBrainStore';
import { BrainRef, FunctionRow } from '../../core/types';
import { Card, Empty, FLUID, Loading, SectionHeader, fieldClass } from '../../ui/primitives';
import { FunctionItem } from './FunctionItem';

const SIDES = ['supervisor', 'core'] as const;

export const FunctionsSection: React.FC = () => {
  const { t } = useSectionText('functions');
  const base = useBrainText();
  const { version, pool } = useBrain();
  const functions = usePolled(fetchFunctions, 'brain_functions_unavailable', true, 0);
  const [query, setQuery] = useState('');
  const { refresh, setData } = functions;
  useEffect(() => {
    if (version > 0) refresh();
  }, [version, refresh]);

  const label = (row: FunctionRow) => {
    const key = `fn_${row.id}`;
    const value = t(key);
    return value === key ? row.id.replace(/_/g, ' ') : value;
  };

  const known = useMemo(() => {
    const map = new Map<string, BrainRef>();
    pool.forEach((item) => map.set(item.ref, item));
    (functions.data ?? []).forEach((row) => row.chain.forEach((ref) => map.set(ref.ref, ref)));
    return map;
  }, [pool, functions.data]);

  if (!functions.data) {
    return <Loading label={base.t('loading')} />;
  }
  const visible = functions.data.filter((row) => matches(query, label(row), row.id));
  const custom = functions.data.filter((row) => row.mode !== 'inherit').length;

  return (
    <>
      <SectionHeader title={t('title')} description={t('description')} />
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <label className="relative min-w-0 flex-1">
          <span className="sr-only">{t('search')}</span>
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
          <input value={query} maxLength={60} onChange={(e) => setQuery(e.target.value)} placeholder={t('search')} className={`${fieldClass} pl-9`} />
        </label>
        <p className="shrink-0 text-xs text-slate-500">{t('custom_count', { n: custom })}</p>
      </div>
      <div className={`grid items-start gap-4 ${FLUID.lg}`}>
      {SIDES.map((side) => {
        const rows = visible.filter((row) => row.side === side);
        return (
          <Card key={side} title={t(`side_${side}`)} description={t(`side_${side}_hint`)} flush>
            {rows.length === 0 ? (
              <div className="p-4"><Empty>{t('empty')}</Empty></div>
            ) : (
              <ul>
                {rows.map((row) => (
                  <FunctionItem key={row.id} row={row} label={label(row)} known={known} onSaved={setData} />
                ))}
              </ul>
            )}
          </Card>
        );
      })}
      </div>
    </>
  );
};
