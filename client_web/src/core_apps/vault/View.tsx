import React, { useState } from 'react';
import { FileText, FolderLock, RefreshCw } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { AppFrame, Btn, Empty, List, Loading, Panel, Pill, Row, Stat, StatRow, Unreachable, formatTime } from '../shared/kit';
import { useAction, useResource } from '../shared/useResource';
import { syncVault } from './api';
import { VaultOverview } from './types';

export const View: React.FC = () => {
  const { t, lang } = useScopedI18n('core_apps/vault');
  const { data, error, loading, reload } = useResource<VaultOverview>('/api/vault', 30000);
  const { busy, run } = useAction(reload);
  const [result, setResult] = useState<{ written: number; imported: number } | null>(null);

  if (loading && !data) {
    return <Loading label={t('loading')} />;
  }
  if (!data) {
    return <Unreachable label={t(error ? 'unreachable' : 'loading')} />;
  }

  const sync = async () => {
    const out = await run(syncVault, 'vault_sync_failed');
    if (out) {
      setResult({ written: out.written, imported: out.imported.length });
    }
  };

  return (
    <AppFrame
      title={t('title')}
      description={t('description')}
      onReload={reload}
      actions={
        <Btn busy={busy} disabled={!data.enabled} onClick={() => void sync()}>
          <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
          {t('sync')}
        </Btn>
      }
    >
      <StatRow>
        <Stat label={t('stat_state')} value={data.enabled ? t('on') : t('off')} tone={data.enabled ? 'emerald' : 'slate'} />
        <Stat label={t('stat_files')} value={data.files.length} />
        <Stat label={t('stat_last_export')} value={formatTime(data.last_export, lang)} tone="amber" />
      </StatRow>
      {result ? <Pill tone="emerald">{t('sync_done', { written: result.written, imported: result.imported })}</Pill> : null}
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title={t('files_title')} icon={<FolderLock className="h-4 w-4 text-rose-300" aria-hidden="true" />}>
          <p className="mb-3 break-all font-mono text-[11px] text-slate-500">{data.root}</p>
          {data.files.length === 0 ? (
            <Empty>{t('files_empty')}</Empty>
          ) : (
            <List>
              {data.files.map((file) => (
                <Row key={file}>
                  <span className="break-all font-mono text-xs">{file}</span>
                </Row>
              ))}
            </List>
          )}
        </Panel>
        <Panel title={t('diary_title')} icon={<FileText className="h-4 w-4 text-cyan-300" aria-hidden="true" />}>
          {data.today ? <pre className="max-h-[60vh] overflow-auto whitespace-pre-wrap text-xs leading-relaxed text-slate-300">{data.today}</pre> : <Empty>{t('diary_empty')}</Empty>}
        </Panel>
      </div>
    </AppFrame>
  );
};

export default View;
