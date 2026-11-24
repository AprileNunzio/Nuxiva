import React from 'react';
import { Diagnosis, hintKey, outcomeKey } from '../diagnosis/diagnose';
import { requestLabel } from '../diagnosis/report';
import { serverCodeLabel } from '../errorTitle';

type Translate = (key: string, params?: Record<string, string | number>) => string;

interface Props {
  readonly t: Translate;
  readonly code: string;
  readonly occurredAt: number;
  readonly diagnosis: Diagnosis;
  readonly lang: string;
}

interface Row {
  readonly label: string;
  readonly value: string;
  readonly mono?: boolean;
}

export function detailRows(t: Translate, code: string, occurredAt: number, diagnosis: Diagnosis, lang: string): Row[] {
  const rows: Row[] = [];
  const request = requestLabel(diagnosis);
  if (request) rows.push({ label: t('detail_request'), value: request, mono: true });
  const outcome = t(outcomeKey(diagnosis), { status: diagnosis.status ?? '-' });
  rows.push({ label: t('detail_outcome'), value: diagnosis.status !== null && diagnosis.kind === 'http' ? `${outcome} (HTTP ${diagnosis.status})` : outcome });
  if (diagnosis.serverCode) rows.push({ label: t('detail_server_code'), value: serverCodeLabel(t, diagnosis.serverCode) });
  if (diagnosis.serverMessage) rows.push({ label: t('detail_server_message'), value: diagnosis.serverMessage });
  if (diagnosis.elapsedMs !== null) rows.push({ label: t('detail_duration'), value: t('detail_duration_value', { ms: diagnosis.elapsedMs }) });
  rows.push({ label: t('detail_internal_code'), value: code, mono: true });
  rows.push({ label: t('detail_time'), value: new Date(occurredAt).toLocaleTimeString(lang) });
  rows.push({ label: t('detail_raw'), value: diagnosis.raw, mono: true });
  return rows;
}

export const ErrorDetails: React.FC<Props> = ({ t, code, occurredAt, diagnosis, lang }) => (
  <div className="mt-1 space-y-2">
    <p className="text-xs opacity-95">
      <span className="font-semibold">{t('detail_what_to_do')}: </span>
      {t(hintKey(diagnosis))}
    </p>
    <dl className="grid grid-cols-[auto_1fr] gap-x-2 gap-y-0.5 text-[11px] leading-snug text-slate-300">
      {detailRows(t, code, occurredAt, diagnosis, lang).map((row) => (
        <React.Fragment key={row.label}>
          <dt className="text-slate-400">{row.label}</dt>
          <dd className={`min-w-0 break-words ${row.mono ? 'font-mono' : ''}`}>{row.value}</dd>
        </React.Fragment>
      ))}
    </dl>
  </div>
);
