import React from 'react';
import { CheckCircle2, ShieldAlert } from 'lucide-react';
import { formatBytes, formatTime, Panel, Pill, Row, List } from '../../shared/kit';
import { ResetReport, Translate } from '../types';

interface Props {
  readonly report: ResetReport | null;
  readonly lang: string;
  readonly t: Translate;
  readonly title?: string;
}

const Check: React.FC<{ readonly ok: boolean; readonly label: string; readonly detail?: string }> = ({ ok, label, detail }) => (
  <Row actions={<Pill tone={ok ? 'emerald' : 'rose'}>{ok ? 'OK' : '!'}</Pill>}>
    <div className="min-w-0">
      <p className="text-sm text-slate-100">{label}</p>
      {detail ? <p className="text-xs text-slate-500">{detail}</p> : null}
    </div>
  </Row>
);

export const ReportPanel: React.FC<Props> = ({ report, lang, t, title }) => {
  if (report === null) {
    return (
      <Panel title={title ?? t('report_title')}>
        <p className="text-sm text-slate-300">{t('report_signed_out')}</p>
      </Panel>
    );
  }
  const verified = report.status === 'verified';
  const leftovers = Object.values(report.leftovers).flat().length;
  const removedFiles = report.roots.reduce((sum, row) => sum + row.files, 0);
  const removedBytes = report.roots.reduce((sum, row) => sum + row.bytes, 0);
  const failed = report.roots.reduce((sum, row) => sum + row.failed, 0);
  return (
    <Panel
      title={title ?? t('report_title')}
      icon={verified ? <CheckCircle2 className="h-4 w-4 text-emerald-300" aria-hidden="true" /> : <ShieldAlert className="h-4 w-4 text-rose-300" aria-hidden="true" />}
    >
      <p className={`mb-3 text-sm font-semibold ${verified ? 'text-emerald-300' : 'text-rose-300'}`} role="status">
        {t(verified ? 'report_verified' : 'report_incomplete')}
      </p>
      <p className="mb-3 text-xs text-slate-500">{t('report_when', { time: formatTime(report.finished, lang) })}</p>
      <List>
        <Check ok={failed === 0} label={t('check_removed', { files: removedFiles, size: formatBytes(removedBytes) })} detail={failed ? t('check_failed', { n: failed }) : undefined} />
        <Check ok={leftovers === 0} label={t('check_leftovers')} detail={leftovers ? t('check_leftovers_n', { n: leftovers }) : undefined} />
        <Check ok={report.canariesSurvivors === 0} label={t('check_canaries', { n: report.canariesChecked })} />
        <Check ok={report.openDeleted === 0} label={t('check_open')} detail={report.openDeleted ? t('check_open_n', { n: report.openDeleted }) : undefined} />
        <Check ok label={t('check_secrets', { rotated: report.envRotated, removed: report.envRemoved })} />
        <Check ok={report.notStarted.length === 0} label={t('check_services')} detail={report.notStarted.length ? report.notStarted.join(', ') : undefined} />
      </List>
      {report.kept.length ? <p className="mt-3 text-xs text-amber-300/80">{t('report_kept', { items: report.kept.join(', ') })}</p> : null}
      {report.skippedMounts ? <p className="mt-2 text-xs text-amber-300/80">{t('report_mounts', { n: report.skippedMounts })}</p> : null}
      <p className="mt-3 text-xs text-slate-500">{t('report_ssd_note')}</p>
      {verified ? <p className="mt-2 text-sm text-slate-300">{t('report_next')}</p> : null}
    </Panel>
  );
};
