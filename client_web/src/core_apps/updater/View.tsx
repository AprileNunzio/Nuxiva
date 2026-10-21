import React from 'react';
import { ApplicationLayout } from '../../app_shell/window_manager/ApplicationLayout';
import './updater.css';
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

  if (!status) return <ApplicationLayout sections={{}} loading={!unreachable} error={unreachable ? t('status_unreachable') : undefined} onRetry={refresh}/>;
  return <ApplicationLayout parameters={{count:status.nodes.length}} contentClassName="update-workbench" sections={{
    overview:<VersionHero status={status} applying={applying} unreachable={unreachable} onStatus={setStatus} onApplying={markApplying}/>,
    releases:<ChangelogPanel entries={status.changelog}/>,
    nodes:<RolloutPanel nodes={status.nodes} onChanged={refresh}/>,
    diagnostics:<CollaudoPanel/>,
    policy:<PolicyPanel status={status} onStatus={setStatus}/>,
    history:<HistoryPanel refreshKey={`${status.local_rev}-${status.last_check}-${status.phase}`}/>,
  }}/>;
};
export default View;
