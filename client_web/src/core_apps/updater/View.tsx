import React from 'react';
import { Loader2, WifiOff } from 'lucide-react';
import { ChangelogPanel } from './components/ChangelogPanel';
import { CollaudoPanel } from './components/CollaudoPanel';
import { HistoryPanel } from './components/HistoryPanel';
import { PolicyPanel } from './components/PolicyPanel';
import { RolloutPanel } from './components/RolloutPanel';
import { VersionHero } from './components/VersionHero';
import { useUpdaterStatus } from './hooks/useUpdaterStatus';
import { useUpdaterI18n } from './scope';

export const View: React.FC = () => {
  const { t } = useUpdaterI18n();
  const { status, unreachable, applying, setStatus, markApplying, refresh } = useUpdaterStatus();

  if (!status) {
    return (
      <div className="flex min-h-[40vh] flex-col items-center justify-center gap-3 text-sm text-slate-400" role="status">
        {unreachable ? <WifiOff className="h-6 w-6 text-rose-300" aria-hidden="true" /> : <Loader2 className="h-6 w-6 animate-spin text-cyan-300" aria-hidden="true" />}
        {t(unreachable ? 'status_unreachable' : 'loading')}
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-4 px-3 py-4 sm:px-6">
      <VersionHero status={status} applying={applying} unreachable={unreachable} onStatus={setStatus} onApplying={markApplying} />
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <div className="flex min-w-0 flex-col gap-4">
          <ChangelogPanel entries={status.changelog} />
          <RolloutPanel nodes={status.nodes} onChanged={refresh} />
          <CollaudoPanel />
        </div>
        <div className="flex min-w-0 flex-col gap-4">
          <PolicyPanel status={status} onStatus={setStatus} />
          <HistoryPanel refreshKey={`${status.local_rev}-${status.last_check}-${status.phase}`} />
        </div>
      </div>
    </div>
  );
};

export default View;
