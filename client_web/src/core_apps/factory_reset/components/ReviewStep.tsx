import React, { useState } from 'react';
import { AlertTriangle, Download } from 'lucide-react';
import { Btn, Empty, formatBytes, Panel, Pill, Stat, StatRow, Toggle } from '../../shared/kit';
import { createBackup, reasonCode } from '../api';
import { ResetInventory, ResetOptions, Translate } from '../types';

interface Props {
  readonly inventory: ResetInventory;
  readonly options: ResetOptions;
  readonly onOptions: (next: ResetOptions) => void;
  readonly onContinue: () => void;
  readonly t: Translate;
}

export const ReviewStep: React.FC<Props> = ({ inventory, options, onOptions, onContinue, t }) => {
  const [backup, setBackup] = useState<{ busy: boolean; url: string; error: string }>({ busy: false, url: '', error: '' });
  const peak = Math.max(1, ...inventory.domains.map((domain) => domain.bytes));
  const blocked = inventory.blockers.length > 0;

  const makeBackup = async () => {
    setBackup({ busy: true, url: '', error: '' });
    try {
      setBackup({ busy: false, url: await createBackup(), error: '' });
    } catch (cause) {
      setBackup({ busy: false, url: '', error: t(`err_${reasonCode(cause)}`) });
    }
  };

  return (
    <div className="grid gap-4">
      <div role="alert" className="flex gap-3 rounded-2xl border border-rose-500/40 bg-rose-500/10 p-4 text-sm text-rose-100">
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-rose-300" aria-hidden="true" />
        <div>
          <p className="font-semibold">{t('warning_title')}</p>
          <p className="mt-1 text-rose-100/80">{t('warning_body')}</p>
        </div>
      </div>
      <StatRow>
        <Stat label={t('stat_files')} value={inventory.files} tone="rose" />
        <Stat label={t('stat_size')} value={formatBytes(inventory.bytes)} tone="amber" />
        <Stat label={t('stat_groups')} value={inventory.domains.length} tone="cyan" />
      </StatRow>
      <Panel title={t('inventory_title')}>
        {inventory.domains.length === 0 ? (
          <Empty>{t('inventory_empty')}</Empty>
        ) : (
          <ul className="grid gap-2">
            {inventory.domains.map((domain) => (
              <li key={domain.id} className="rounded-xl border border-slate-800 bg-slate-900/40 p-3">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <span className="text-sm font-semibold text-slate-100">{t(`domain_${domain.id}`)}</span>
                  <span className="text-xs text-slate-400">{t('domain_detail', { files: domain.files, size: formatBytes(domain.bytes) })}</span>
                </div>
                <p className="mt-1 text-xs text-slate-500">{t(`domain_${domain.id}_hint`)}</p>
                <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-800" aria-hidden="true">
                  <div className="h-full rounded-full bg-rose-400/70" style={{ width: `${Math.max(2, Math.round((domain.bytes / peak) * 100))}%` }} />
                </div>
              </li>
            ))}
          </ul>
        )}
      </Panel>
      <Panel title={t('options_title')}>
        <div className="grid gap-3">
          <Toggle checked={options.keepBackups} onChange={(value) => onOptions({ ...options, keepBackups: value })} label={t('option_keep_backups')} />
          <Toggle checked={options.includeShares} onChange={(value) => onOptions({ ...options, includeShares: value })} label={t('option_shares')} />
          <p className="text-xs text-slate-500">{t('keeps_note')}</p>
        </div>
      </Panel>
      <Panel title={t('backup_title')}>
        <p className="mb-3 text-xs text-slate-400">{t('backup_hint')}</p>
        <div className="flex flex-wrap items-center gap-3">
          <Btn tone="slate" busy={backup.busy} onClick={() => void makeBackup()}>
            {t('backup_make')}
          </Btn>
          {backup.url ? (
            <a className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-300 underline" href={backup.url} download>
              <Download className="h-3.5 w-3.5" aria-hidden="true" />
              {t('backup_download')}
            </a>
          ) : null}
          {backup.error ? <Pill tone="rose">{backup.error}</Pill> : null}
        </div>
        <p className="mt-2 text-xs text-amber-300/80">{t('backup_plain_note')}</p>
      </Panel>
      {blocked ? <Pill tone="amber">{t(`err_${inventory.blockers[0]}`)}</Pill> : null}
      <div className="flex justify-end">
        <Btn tone="rose" disabled={blocked || inventory.domains.length === 0} onClick={onContinue}>
          {t('continue')}
        </Btn>
      </div>
    </div>
  );
};
