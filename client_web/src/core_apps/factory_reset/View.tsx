import React, { useCallback, useState } from 'react';
import { RotateCcw } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { AppFrame, Btn, Loading, Unreachable } from '../shared/kit';
import { useResource } from '../shared/useResource';
import { inventoryUrl, parseInventory } from './api';
import { ConfirmStep } from './components/ConfirmStep';
import { IdentityStep } from './components/IdentityStep';
import { ProgressStep } from './components/ProgressStep';
import { ReportPanel } from './components/ReportPanel';
import { ReviewStep } from './components/ReviewStep';
import { StepBar } from './components/StepBar';
import { ResetChallenge, ResetOptions, ResetReport, ResetStage } from './types';

export const View: React.FC = () => {
  const { t, lang } = useScopedI18n('core_apps/factory_reset');
  const [options, setOptions] = useState<ResetOptions>({ keepBackups: false, includeShares: false });
  const [stage, setStage] = useState<ResetStage>('review');
  const [challenge, setChallenge] = useState<ResetChallenge | null>(null);
  const [resetId, setResetId] = useState('');
  const [report, setReport] = useState<ResetReport | null>(null);
  const { data, error, loading, reload } = useResource<unknown>(inventoryUrl(options));
  const inventory = data === null ? null : parseInventory(data);

  const expired = useCallback(() => {
    setChallenge(null);
    setStage('identity');
  }, []);
  const finished = useCallback((result: ResetReport | null) => {
    setReport(result);
    setStage('done');
  }, []);

  if (loading && !inventory && stage === 'review') {
    return <Loading label={t('loading')} />;
  }
  if (!inventory && stage === 'review') {
    return <Unreachable label={t(error ? 'unreachable' : 'loading')} />;
  }

  return (
    <AppFrame title={t('title')} description={t('description')} onReload={stage === 'review' ? reload : undefined}>
      <StepBar stage={stage} t={t} />
      {stage === 'review' && inventory ? (
        <div className="grid gap-4">
          {inventory.last ? <ReportPanel report={inventory.last} lang={lang} t={t} title={t('last_title')} /> : null}
          <ReviewStep inventory={inventory} options={options} onOptions={setOptions} onContinue={() => setStage('identity')} t={t} />
        </div>
      ) : null}
      {stage === 'identity' ? (
        <IdentityStep
          options={options}
          onBack={() => setStage('review')}
          onIssued={(issued) => {
            setChallenge(issued);
            setStage('confirm');
          }}
          t={t}
        />
      ) : null}
      {stage === 'confirm' && challenge ? (
        <ConfirmStep
          challenge={challenge}
          options={options}
          onBack={expired}
          onExpired={expired}
          onStarted={(id) => {
            setChallenge(null);
            setResetId(id);
            setStage('running');
          }}
          t={t}
        />
      ) : null}
      {stage === 'running' ? <ProgressStep resetId={resetId} onFinished={finished} t={t} /> : null}
      {stage === 'done' ? (
        <div className="grid gap-4">
          <ReportPanel report={report} lang={lang} t={t} />
          <div className="flex justify-end">
            <Btn tone="slate" onClick={() => window.location.reload()}>
              <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
              {t('reload')}
            </Btn>
          </div>
        </div>
      ) : null}
    </AppFrame>
  );
};

export default View;
