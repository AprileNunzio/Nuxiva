import { McpAudit, McpAuditRecord } from './types';

export const AUDIT_SHOWN = 40;

export function recentAuditRecords(audit: McpAudit | null | undefined, limit: number = AUDIT_SHOWN): readonly McpAuditRecord[] {
  const records: unknown = audit?.records;
  if (!Array.isArray(records) || limit <= 0) return [];
  return records
    .filter((record): record is McpAuditRecord => typeof record === 'object' && record !== null && typeof record.hash === 'string' && typeof record.event === 'object' && record.event !== null)
    .slice(-limit)
    .reverse();
}

export function auditCount(audit: McpAudit | null | undefined): number {
  const count: unknown = audit?.count;
  return typeof count === 'number' && Number.isFinite(count) && count >= 0 ? count : 0;
}
