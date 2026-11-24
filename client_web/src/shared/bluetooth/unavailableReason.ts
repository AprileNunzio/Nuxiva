import { Diagnosis } from '../errors/diagnosis/diagnose';

export function unavailableCode(diagnosis: Diagnosis): string {
  if (diagnosis.kind !== 'http' || diagnosis.status === null) {
    return 'node_bluetooth_unavailable';
  }
  if (diagnosis.status === 401 || diagnosis.status === 403) {
    return 'node_bluetooth_forbidden';
  }
  if (diagnosis.status === 404 || diagnosis.status === 405) {
    return 'node_bluetooth_unsupported';
  }
  if (diagnosis.status === 409 || diagnosis.serverCode === 'bluetooth_adapter_not_ready') {
    return 'node_bluetooth_adapter_missing';
  }
  if (diagnosis.status >= 500) {
    return 'node_bluetooth_service_failed';
  }
  return 'node_bluetooth_unavailable';
}
