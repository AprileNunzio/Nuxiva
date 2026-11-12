import React, { useState } from 'react';
import { Send } from 'lucide-react';
import { useAction } from '../../../../node_apps/shared/hooks/useAction';
import { testRoute } from '../../core/brainApi';
import { useBrainText, useSectionText } from '../../core/i18n';
import { RouteResult } from '../../core/types';
import { Button, Card, fieldClass } from '../../ui/primitives';

export const RouteTester: React.FC = () => {
  const { t } = useSectionText('contexts');
  const base = useBrainText();
  const action = useAction();
  const [text, setText] = useState('');
  const [result, setResult] = useState<RouteResult | null>(null);
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    const clean = text.trim();
    if (!clean) return;
    const outcome = await action.run('route', () => testRoute(clean), 'brain_route_failed');
    if (outcome) setResult(outcome);
  };
  return (
    <Card title={t('tester_title')} description={t('tester_hint')}>
      <form onSubmit={(e) => void submit(e)} className="flex flex-col gap-2 sm:flex-row">
        <label className="min-w-0 flex-1">
          <span className="sr-only">{t('tester_placeholder')}</span>
          <input value={text} maxLength={2000} onChange={(e) => setText(e.target.value)} placeholder={t('tester_placeholder')} className={fieldClass} />
        </label>
        <Button type="submit" variant="primary" icon={Send} busy={action.busy === 'route'} disabled={!text.trim()}>
          {t('tester_submit')}
        </Button>
      </form>
      {result && (
        <div className="mt-3 rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-700" aria-live="polite">
          <p>{t('tester_result', { context: base.t(`role_${result.kind}`) })}</p>
          <p className="mt-1 text-xs text-slate-500">{result.models.length ? result.models.join(' → ') : base.t('none_available')}</p>
        </div>
      )}
    </Card>
  );
};
