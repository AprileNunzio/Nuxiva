import React from 'react';
import { compactNumber } from '../../core/format';
import { useSectionText } from '../../core/i18n';
import { PRIVACY_BUCKETS, PRIVACY_LEVELS, PrivacyOverview } from '../../core/privacyApi';
import { Card } from '../../ui/primitives';

export const AuditCard: React.FC<{ readonly data: PrivacyOverview }> = ({ data }) => {
  const { t, lang } = useSectionText('privacy');
  const n = (value: number) => compactNumber(value, lang);
  return (
    <Card title={t('audit_title')} description={t('audit_hint', { days: data.days })} flush>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[520px] text-left text-sm">
          <thead className="bg-slate-50 text-xs text-slate-500">
            <tr>
              <th scope="col" className="px-4 py-2 font-medium sm:px-5">{t('col_level')}</th>
              {PRIVACY_BUCKETS.map((bucket) => (
                <th key={bucket} scope="col" className="px-3 py-2 text-right font-medium">{t(`bucket_${bucket}`)}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {PRIVACY_LEVELS.map((level) => (
              <tr key={level}>
                <th scope="row" className="px-4 py-2.5 font-medium text-slate-900 sm:px-5">{t(`level_${level}`)}</th>
                {PRIVACY_BUCKETS.map((bucket) => {
                  const value = data.total[level][bucket];
                  const alert = bucket === 'blocked' && value > 0;
                  return (
                    <td key={bucket} className={`px-3 py-2.5 text-right tabular-nums ${alert ? 'font-semibold text-amber-700' : 'text-slate-700'}`}>
                      {n(value)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
};
