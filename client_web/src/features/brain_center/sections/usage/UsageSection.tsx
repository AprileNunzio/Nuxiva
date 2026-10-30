import React, { useEffect } from 'react';
import { usePolled } from '../../../../node_apps/shared/hooks/useAction';
import { compactNumber, share } from '../../core/format';
import { useBrainText, useSectionText } from '../../core/i18n';
import { fetchUsage } from '../../core/usageApi';
import { useBrain } from '../../core/useBrainStore';
import { UsageSummary } from '../../core/types';
import { Card, Empty, Loading, Meter, SectionHeader } from '../../ui/primitives';
import { BudgetsCard } from './BudgetsCard';
import { DailyChart } from './DailyChart';
import { WidgetCard } from './WidgetCard';

const Stat: React.FC<{ readonly label: string; readonly value: string; readonly children?: React.ReactNode }> = ({ label, value, children }) => (
  <div className="flex flex-col gap-1 rounded-xl border border-slate-200 bg-white p-4 shadow-2xs">
    <p className="text-xs text-slate-500">{label}</p>
    <p className="text-2xl font-semibold tracking-tight text-slate-900">{value}</p>
    {children}
  </div>
);

export const UsageSection: React.FC = () => {
  const { t, lang } = useSectionText('usage');
  const base = useBrainText();
  const { version } = useBrain();
  const usage = usePolled(fetchUsage, 'brain_usage_unavailable', true, 20000);
  const { refresh, setData } = usage;
  useEffect(() => {
    if (version > 0) refresh();
  }, [version, refresh]);
  const data = usage.data;
  if (!data) {
    return <Loading label={base.t('loading')} />;
  }
  const n = (value: number) => compactNumber(value, lang);
  const used = share(data.cloud, data.globalBudget);

  return (
    <>
      <SectionHeader title={t('title')} description={t('description', { month: data.month })} />
      <div className="grid gap-3 sm:grid-cols-3">
        <Stat label={t('today')} value={n(data.today)} />
        <Stat label={t('month_total')} value={n(data.total)} />
        <Stat label={t('month_cloud')} value={n(data.cloud)}>
          {used !== null && data.globalBudget !== null ? (
            <>
              <Meter value={used} label={t('budget_global')} />
              <p className="text-xs text-slate-500">{t('of_budget', { cap: n(data.globalBudget) })}</p>
            </>
          ) : (
            <p className="text-xs text-slate-500">{t('no_budget')}</p>
          )}
        </Stat>
      </div>
      <DailyChart days={data.days} />
      <ProviderTable data={data} />
      <BudgetsCard data={data} onSaved={setData} />
      <WidgetCard />
    </>
  );
};

const ProviderTable: React.FC<{ readonly data: UsageSummary }> = ({ data }) => {
  const { t, lang } = useSectionText('usage');
  const base = useBrainText();
  const n = (value: number) => compactNumber(value, lang);
  return (
    <Card title={t('by_provider')} flush>
      {data.providers.length === 0 ? (
        <div className="p-4"><Empty>{t('empty')}</Empty></div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[520px] text-left text-sm">
            <thead className="bg-slate-50 text-xs text-slate-500">
              <tr>
                <th scope="col" className="px-4 py-2 font-medium sm:px-5">{t('col_provider')}</th>
                <th scope="col" className="px-3 py-2 text-right font-medium">{t('col_in')}</th>
                <th scope="col" className="px-3 py-2 text-right font-medium">{t('col_out')}</th>
                <th scope="col" className="px-3 py-2 text-right font-medium">{t('col_calls')}</th>
                <th scope="col" className="px-4 py-2 font-medium sm:px-5">{t('col_budget')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.providers.map((row) => {
                const ratio = share(row.tokensIn + row.tokensOut, row.budget);
                return (
                  <tr key={row.id}>
                    <th scope="row" className="px-4 py-2.5 font-medium text-slate-900 sm:px-5">{row.id === 'local' ? base.t('origin_local') : row.id}</th>
                    <td className="px-3 py-2.5 text-right tabular-nums text-slate-700">{n(row.tokensIn)}</td>
                    <td className="px-3 py-2.5 text-right tabular-nums text-slate-700">{n(row.tokensOut)}</td>
                    <td className="px-3 py-2.5 text-right tabular-nums text-slate-700">{n(row.calls)}</td>
                    <td className="px-4 py-2.5 sm:px-5">
                      {ratio !== null && row.budget !== null ? (
                        <div className="flex min-w-[120px] flex-col gap-1">
                          <Meter value={ratio} label={t('col_budget')} />
                          <span className="text-[11px] text-slate-500">{t('of_budget', { cap: n(row.budget) })}</span>
                        </div>
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
};
