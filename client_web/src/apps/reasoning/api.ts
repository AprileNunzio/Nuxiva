import { sendJson } from '../shared/http';
import type { Config, Mode, Status } from './types';

export const BASE = '/api/v5/reasoning';
export const statusUrl = `${BASE}/status`;
export const tracesUrl = `${BASE}/traces?limit=100`;

export const setMode = (mode: Mode, force: boolean) => sendJson<Status>(`${BASE}/mode`, 'POST', { mode, force });
export const killSwitch = () => sendJson<Status>(`${BASE}/kill`, 'POST');
export const saveConfig = (config: Config) => sendJson<Status>(`${BASE}/config`, 'PUT', config);
export const resetLedger = () => sendJson<Status>(`${BASE}/ledger/reset`, 'POST');
export const refreshInventory = () => sendJson<Status>(`${BASE}/inventory/refresh`, 'POST');
