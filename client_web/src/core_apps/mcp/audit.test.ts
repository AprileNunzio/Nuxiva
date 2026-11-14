import { describe, expect, it } from 'vitest';
import { auditCount, recentAuditRecords } from './audit';
import { McpAudit, McpAuditRecord } from './types';

const record = (seq: number): McpAuditRecord =>
  ({ seq, hash: `h${seq}`, event: { ts_ms: seq, agent: 'a', server: 's', tool: 't', risk: 'low', verdict: 'completed', duration_ms: 1 } }) as unknown as McpAuditRecord;

const audit = (records: unknown, count: unknown = 0): McpAudit => ({ intact: true, error: null, count, head: '', records }) as unknown as McpAudit;

describe('recentAuditRecords', () => {
  it('returns an empty list when there is no audit', () => {
    expect(recentAuditRecords(null)).toEqual([]);
    expect(recentAuditRecords(undefined)).toEqual([]);
  });

  it.each([null, undefined, {}, 'x', 7])('survives a non iterable records value %p', (records) => {
    expect(recentAuditRecords(audit(records))).toEqual([]);
  });

  it('returns the newest records first and bounded by the limit', () => {
    const rows = recentAuditRecords(audit(Array.from({ length: 5 }, (_, i) => record(i))), 3);
    expect(rows.map((row) => row.seq)).toEqual([4, 3, 2]);
  });

  it('drops malformed entries', () => {
    const rows = recentAuditRecords(audit([record(1), null, 3, { hash: 'x' }, record(2)]));
    expect(rows.map((row) => row.seq)).toEqual([2, 1]);
  });

  it('does not mutate the source', () => {
    const source = [record(1), record(2)];
    recentAuditRecords(audit(source));
    expect(source.map((row) => row.seq)).toEqual([1, 2]);
  });
});

describe('auditCount', () => {
  it('accepts only finite non negative numbers', () => {
    expect(auditCount(audit([], 12))).toBe(12);
    expect(auditCount(audit([], null))).toBe(0);
    expect(auditCount(audit([], -1))).toBe(0);
    expect(auditCount(audit([], Number.NaN))).toBe(0);
    expect(auditCount(null)).toBe(0);
  });
});
