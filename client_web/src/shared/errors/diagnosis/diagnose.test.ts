import { describe, expect, it } from 'vitest';
import { FetchFailure, guardFetch } from '../../http/fetchFailure';
import { NodeModuleError } from '../../../node_apps/shared/data/http';
import { diagnose, hintKey, isConnectivityFailure, outcomeKey } from './diagnose';
import { buildReport, requestLabel, serializeReports } from './report';

describe('diagnose', () => {
  it('turns a bare Failed to fetch into an unreachable server', () => {
    const d = diagnose(new TypeError('Failed to fetch'));
    expect(d.kind).toBe('unreachable');
    expect(isConnectivityFailure(d)).toBe(true);
    expect(hintKey(d)).toBe('hint_unreachable');
  });

  it('keeps method, path and duration from a guarded fetch', async () => {
    const failure = await guardFetch(() => Promise.reject(new TypeError('Failed to fetch')), 'GET', '/api/bluetooth').catch((e: unknown) => e);
    expect(failure).toBeInstanceOf(FetchFailure);
    const d = diagnose(failure);
    expect(d.kind).toBe('unreachable');
    expect(requestLabel(d)).toBe('GET /api/bluetooth');
    expect(d.elapsedMs).toBeGreaterThanOrEqual(0);
  });

  it('lets aborts through untouched', async () => {
    const abort = Object.assign(new Error('stop'), { name: 'AbortError' });
    const result = await guardFetch(() => Promise.reject(abort), 'GET', '/x').catch((e: unknown) => e);
    expect(result).toBe(abort);
    expect(diagnose(result).kind).toBe('aborted');
  });

  it('marks offline devices separately', () => {
    expect(diagnose(new FetchFailure('POST', '/api/x', false, 3, 'Failed to fetch')).kind).toBe('offline');
  });

  it('reads status, server code and message from HTTP errors', () => {
    const d = diagnose(new NodeModuleError('bluetooth_adapter_not_ready', 409, 'no adapter', 'POST', '/api/bluetooth/scan'));
    expect(d).toMatchObject({ kind: 'http', status: 409, serverCode: 'bluetooth_adapter_not_ready', serverMessage: 'no adapter' });
    expect(requestLabel(d)).toBe('POST /api/bluetooth/scan');
    expect(hintKey(d)).toBe('hint_http_409');
    expect(outcomeKey(d)).toBe('outcome_http');
  });

  it('hides the generic request_failed code and maps unknown 5xx', () => {
    const d = diagnose(new NodeModuleError('request_failed', 507));
    expect(d.serverCode).toBeNull();
    expect(hintKey(d)).toBe('hint_http_500');
  });

  it('recognises unreadable answers', () => {
    expect(diagnose(new NodeModuleError('invalid_response', 200, 'Unexpected token <')).kind).toBe('invalid_response');
    expect(diagnose(new SyntaxError('bad json')).kind).toBe('invalid_response');
  });

  it('strips control characters and rejects unsafe paths', () => {
    const d = diagnose(new NodeModuleError('x', 500, 'line\u0000break‮', 'GET', '/api/x?token=secret'));
    expect(d.serverMessage).toBe('line break');
    expect(d.path).toBeNull();
  });

  it('builds a copyable report without query strings', () => {
    const d = diagnose(new FetchFailure('GET', '/api/state', true, 12, 'Failed to fetch'));
    const report = buildReport('core_app_load_failed', Date.UTC(2026, 10, 24, 9, 40), d, '/dashboard?session=abc');
    expect(report).toMatchObject({ code: 'core_app_load_failed', request: 'GET /api/state', page: '/dashboard', kind: 'unreachable' });
    expect(JSON.parse(serializeReports([report, report]))).toHaveLength(2);
  });
});
