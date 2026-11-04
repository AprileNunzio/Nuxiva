import React from 'react';
import { ArrowRight } from 'lucide-react';
import { usePolled } from '../../../../node_apps/shared/hooks/useAction';
import { compactNumber, share } from '../../core/format';
import { useBrainText, useSectionText } from '../../core/i18n';
import { fetchUsage } from '../../core/usageApi';
import { Button, Card, Loading, Meter } from '../../ui/primitives';

export const UsageGlance: React.FC<{ readonly onOpen: () => void }> = ({ onOpen }) => {
  const { t, lang } = useSectionText('overview');
  const base = useBrainText();
  const usage = usePolled(fetchUsage, 'brain_usage_unavailable', true, 30000);
  const data = usage.data;
  const used = data ? share(data.cloud, data.globalBudget) : null;
  return (
    <Card title={t('usage_title')} actions={<Button compact variant="ghost" icon={ArrowRight} onClick={onOpen}>{t('details')}</Button>}>
      {!data ? (
        <Loading label={base.t('loading')} />
      ) : (
        <div className="flex flex-col gap-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="text-xs text-slate-500">{t('usage_today')}</p>
              <p className="text-lg font-semibold text-slate-900">{compactNumber(data.today, lang)}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">{t('usage_month')}</p>
              <p className="text-lg font-semibold text-slate-900">{compactNumber(data.total, lang)}</p>
            </div>
          </div>
          {used !== null && data.globalBudget !== null ? (
            <div className="flex flex-col gap-1">
              <Meter value={used} label={t('usage_budget')} />
              <p className="text-xs text-slate-500">{t('usage_budget_value', { used: compactNumber(data.cloud, lang), cap: compactNumber(data.globalBudget, lang) })}</p>
            </div>
          ) : (
            <p className="text-xs text-slate-500">{t('usage_no_budget')}</p>
          )}
        </div>
      )}
    </Card>
  );
};
