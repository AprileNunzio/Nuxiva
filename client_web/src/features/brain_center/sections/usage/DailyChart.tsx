import React from 'react';
import { compactNumber } from '../../core/format';
import { useSectionText } from '../../core/i18n';
import { Card, Empty } from '../../ui/primitives';

export const DailyChart: React.FC<{ readonly days: readonly { readonly date: string; readonly tokens: number }[] }> = ({ days }) => {
  const { t, lang } = useSectionText('usage');
  const peak = Math.max(1, ...days.map((d) => d.tokens));
  const label = (date: string) => new Date(`${date}T12:00:00Z`).toLocaleDateString(lang, { day: 'numeric', month: 'short' });
  return (
    <Card title={t('daily_title')}>
      {days.length === 0 ? (
        <Empty>{t('empty')}</Empty>
      ) : (
        <figure>
          <div className="flex h-36 items-end gap-1" aria-hidden="true">
            {days.map((day) => (
              <div key={day.date} className="group relative flex h-full min-w-0 flex-1 items-end">
                <div className="w-full rounded-t bg-blue-500/80 transition group-hover:bg-blue-600" style={{ height: `${Math.max(2, (day.tokens / peak) * 100)}%` }} />
                <span className="pointer-events-none absolute -top-7 left-1/2 hidden -translate-x-1/2 whitespace-nowrap rounded bg-slate-900 px-1.5 py-0.5 text-[10px] text-white group-hover:block">
                  {label(day.date)} · {compactNumber(day.tokens, lang)}
                </span>
              </div>
            ))}
          </div>
          <div className="mt-1 flex justify-between text-[11px] text-slate-500" aria-hidden="true">
            <span>{label(days[0].date)}</span>
            <span>{label(days[days.length - 1].date)}</span>
          </div>
          <figcaption className="sr-only">
            <table>
              <caption>{t('daily_title')}</caption>
              <tbody>
                {days.map((day) => (
                  <tr key={day.date}>
                    <th scope="row">{label(day.date)}</th>
                    <td>{day.tokens}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </figcaption>
        </figure>
      )}
    </Card>
  );
};
