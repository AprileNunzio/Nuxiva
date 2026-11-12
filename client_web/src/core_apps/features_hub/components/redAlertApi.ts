import { sendJson } from '../../shared/http';

export interface RedAlertStatus {
  readonly enabled: boolean;
  readonly active: boolean;
  readonly message: string;
  readonly seconds: number;
  readonly repeat: number;
  readonly excluded: readonly string[];
}

export interface RedAlertLight {
  readonly id: string;
  readonly name: string;
}

export const redAlertStatusUrl = '/api/redalert';
export const redAlertLightsUrl = '/api/redalert/lights';
export const testRedAlert = () => sendJson('/api/redalert/test', 'POST');
export const stopRedAlert = () => sendJson('/api/redalert/stop', 'POST');
