import React, { useEffect, useMemo, useState } from 'react';
import { Save } from 'lucide-react';
import { usePolled } from '../../../../node_apps/shared/hooks/useAction';
import { parseAmount } from '../../core/format';
import { useBrainText, useSectionText } from '../../core/i18n';
import { fetchProviders } from '../../core/providersApi';
import { saveBudgets } from '../../core/usageApi';
import { useBrain } from '../../core/useBrainStore';
import { UsageSummary } from '../../core/types';
import { Button, Card, Empty, fieldClass } from '../../ui/primitives';

const text = (value: number | null | undefined) => (value ? String(value) : '');

export const BudgetsCard: React.FC<{ readonly data: UsageSummary; readonly onSaved: (summary: UsageSummary) => void }> = ({ data, onSaved }) => {
  const { t } = useSectionText('usage');
  const base = useBrainText();
  const { run, action } = useBrain();
  const providers = usePolled(fetchProviders, 'brain_providers_unavailable', true, 0);
  const [global, setGlobal] = useState(text(data.globalBudget));
  const [caps, setCaps] = useState<Record<string, string>>({});
  const savedKey = JSON.stringify([data.globalBudget, data.providerBudgets]);

  useEffect(() => {
    setGlobal(text(data.globalBudget));
    setCaps(Object.fromEntries(Object.entries(data.providerBudgets).map(([id, v]) => [id, text(v)])));
  }, [savedKey]);

  const configured = useMemo(() => (providers.data ?? []).filter((p) => p.configured || data.providerBudgets[p.id]), [providers.data, data.providerBudgets]);
  const parsedGlobal = parseAmount(global);
  const parsedCaps = Object.fromEntries(configured.map((p) => [p.id, parseAmount(caps[p.id] ?? '')]));
  const valid = parsedGlobal !== undefined && Object.values(parsedCaps).every((v) => v !== undefined);

  const save = async () => {
    if (!valid) return;
    const result = await run('budgets', 'brain_budgets_failed', () =>
      saveBudgets({ global: parsedGlobal ?? null, providers: Object.fromEntries(Object.entries(parsedCaps).map(([id, v]) => [id, v ?? null])) }),
    );
    if (result) onSaved(result);
  };

  const input = (id: string, value: string, onChange: (v: string) => void, label: string) => (
    <label key={id} className="flex flex-col gap-1 text-xs font-medium text-slate-700">
      {label}
      <input
        inputMode="numeric"
        value={value}
        maxLength={17}
        placeholder={t('no_limit')}
        aria-invalid={parseAmount(value) === undefined}
        onChange={(e) => onChange(e.target.value)}
        className={`${fieldClass} tabular-nums ${parseAmount(value) === undefined ? 'border-rose-400' : ''}`}
      />
    </label>
  );

  return (
    <Card
      title={t('budgets_title')}
      description={t('budgets_hint')}
      actions={
        <Button variant="primary" icon={Save} busy={action.busy === 'budgets'} disabled={action.busy !== null || !valid} onClick={() => void save()}>
          {base.t('save')}
        </Button>
      }
    >
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {input('global', global, setGlobal, t('budget_global'))}
        {configured.map((p) => input(p.id, caps[p.id] ?? '', (v) => setCaps({ ...caps, [p.id]: v }), p.name))}
      </div>
      {configured.length === 0 && <div className="mt-3"><Empty>{t('budgets_no_providers')}</Empty></div>}
    </Card>
  );
};
