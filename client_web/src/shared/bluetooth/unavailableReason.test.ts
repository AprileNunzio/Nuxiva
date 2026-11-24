import { describe, expect, it } from 'vitest';
import { NodeModuleError } from '../../node_apps/shared/data/http';
import { FetchFailure } from '../http/fetchFailure';
import { diagnose } from '../errors/diagnosis/diagnose';
import { unavailableCode } from './unavailableReason';

const code = (cause: unknown) => unavailableCode(diagnose(cause));

describe('bluetooth unavailable reason', () => {
  it('explains the real cause', () => {
    expect(code(new NodeModuleError('forbidden', 403))).toBe('node_bluetooth_forbidden');
    expect(code(new NodeModuleError('request_failed', 401))).toBe('node_bluetooth_forbidden');
    expect(code(new NodeModuleError('request_failed', 404))).toBe('node_bluetooth_unsupported');
    expect(code(new NodeModuleError('bluetooth_adapter_not_ready', 409))).toBe('node_bluetooth_adapter_missing');
    expect(code(new NodeModuleError('bluetooth_adapter_unresponsive', 502))).toBe('node_bluetooth_service_failed');
  });

  it('leaves network failures to the grouped server notice', () => {
    expect(code(new FetchFailure('GET', '/api/bluetooth', true, 4, 'Failed to fetch'))).toBe('node_bluetooth_unavailable');
  });
});
