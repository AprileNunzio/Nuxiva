import { Diagnosis } from './diagnose';

export interface DiagnosticReport {
  readonly code: string;
  readonly at: string;
  readonly page: string;
  readonly kind: Diagnosis['kind'];
  readonly request: string | null;
  readonly status: number | null;
  readonly serverCode: string | null;
  readonly serverMessage: string | null;
  readonly elapsedMs: number | null;
  readonly raw: string;
}

export const requestLabel = (diagnosis: Diagnosis): string | null =>
  diagnosis.path ? `${diagnosis.method ?? 'GET'} ${diagnosis.path}` : null;

export function buildReport(code: string, occurredAt: number, diagnosis: Diagnosis, page: string): DiagnosticReport {
  return {
    code,
    at: new Date(occurredAt).toISOString(),
    page: page.split(/[?#]/)[0].slice(0, 200),
    kind: diagnosis.kind,
    request: requestLabel(diagnosis),
    status: diagnosis.status,
    serverCode: diagnosis.serverCode,
    serverMessage: diagnosis.serverMessage,
    elapsedMs: diagnosis.elapsedMs,
    raw: diagnosis.raw,
  };
}

export const serializeReports = (reports: readonly DiagnosticReport[]): string =>
  JSON.stringify(reports.length === 1 ? reports[0] : reports, null, 2);
