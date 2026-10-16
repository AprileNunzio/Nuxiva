import React, { useState } from 'react';
import { Archive, Download, ShieldCheck, Trash2 } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { FeaturePanel } from '../shared/FeaturePanel';
import { AppFrame, Btn, Empty, List, Loading, Panel, Pill, Row, Stat, StatRow, Unreachable, formatBytes, formatTime } from '../shared/kit';
import { useFeature } from '../shared/useFeature';
import { useAction, useResource } from '../shared/useResource';
import { createBackup, deleteBackup, downloadUrl, verifyBackup } from './api';
import { BackupStatus } from './types';

export const View: React.FC = () => {
  const { t, lang } = useScopedI18n('core_apps/backup');
  const status = useResource<BackupStatus>('/api/backup', 8000);
  const settings = useFeature('backup');
  const reloadAll = () => {
    status.reload();
    settings.reload();
  };
  const { busy, run } = useAction(reloadAll);
  const [checks, setChecks] = useState<Readonly<Record<string, boolean>>>({});

  if (status.loading && !status.data) {
    return <Loading label={t('loading')} />;
  }
  if (!status.data) {
    return <Unreachable label={t(status.error ? 'unreachable' : 'loading')} />;
  }
  const { data } = status;

  const verify = async (id: string) => {
    const result = await run(() => verifyBackup(id), 'backup_verify_failed');
    if (result) {
      setChecks((state) => ({ ...state, [id]: result.ok }));
    }
  };

  return (
    <AppFrame
      title={t('title')}
      description={t('description')}
      onReload={reloadAll}
      actions={
        <Btn busy={busy} disabled={!data.enabled} onClick={() => void run(createBackup, 'backup_create_failed')}>
          <Archive className="h-3.5 w-3.5" aria-hidden="true" />
          {t('create')}
        </Btn>
      }
    >
      <StatRow>
        <Stat label={t('stat_count')} value={`${data.items.length}/${data.keep}`} />
        <Stat label={t('stat_size')} value={formatBytes(data.total_size)} tone="purple" />
        <Stat label={t('stat_schedule')} value={data.interval_hours ? t('every_hours', { count: data.interval_hours }) : t('manual')} tone="amber" />
        <Stat label={t('stat_next')} value={formatTime(data.next ?? 0, lang)} tone="emerald" />
      </StatRow>
      <Panel title={t('list_title')}>
        {data.items.length === 0 ? (
          <Empty>{t('empty')}</Empty>
        ) : (
          <List>
            {data.items.map((item) => (
              <Row
                key={item.id}
                actions={
                  <>
                    <Btn tone="slate" busy={busy} title={t('verify')} onClick={() => void verify(item.id)}>
                      <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
                    </Btn>
                    <a className="rounded-xl border border-slate-700 p-2 text-slate-300 hover:border-emerald-500" href={downloadUrl(item.id)} download aria-label={t('download')}>
                      <Download className="h-3.5 w-3.5" aria-hidden="true" />
                    </a>
                    <Btn tone="rose" busy={busy} title={t('delete')} onClick={() => void run(() => deleteBackup(item.id), 'backup_delete_failed')}>
                      <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                    </Btn>
                  </>
                }
              >
                <div className="flex flex-wrap items-center gap-2">
                  <b className="text-sm">{formatTime(item.created, lang)}</b>
                  <Pill tone={item.kind === 'auto' ? 'cyan' : 'slate'}>{item.kind === 'auto' ? t('kind_auto') : t('kind_manual')}</Pill>
                  <span className="text-xs text-slate-400">{formatBytes(item.size)}</span>
                  {item.id in checks ? <Pill tone={checks[item.id] ? 'emerald' : 'rose'}>{checks[item.id] ? t('verified_ok') : t('verified_bad')}</Pill> : null}
                </div>
                <p className="mt-1 break-all font-mono text-[11px] text-slate-500">{item.sha256}</p>
              </Row>
            ))}
          </List>
        )}
      </Panel>
      {settings.feature ? <FeaturePanel feature={settings.feature} busy={busy} t={t} run={run} /> : null}
    </AppFrame>
  );
};

export default View;
