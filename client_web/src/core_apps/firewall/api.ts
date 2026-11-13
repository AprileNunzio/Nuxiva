import { sendJson } from '../shared/http';
import { DefenseState, FirewallRule, RuleDraft, TrustRequest } from './types';

const BASE = '/api/firewall';

export const savePolicy = (change: Readonly<Record<string, unknown>>) => sendJson(`${BASE}/policy`, 'PUT', change);
export const addRule = (draft: RuleDraft) => sendJson(`${BASE}/rules`, 'POST', draft);
export const toggleRule = (rule: FirewallRule, enabled: boolean) => sendJson(`${BASE}/rules/${encodeURIComponent(rule.id)}`, 'PUT', { ...rule, enabled });
export const deleteRule = (id: string) => sendJson(`${BASE}/rules/${encodeURIComponent(id)}`, 'DELETE');
export const blockAddress = (address: string, minutes: number, reason: string) => sendJson(`${BASE}/blocks`, 'POST', { address, minutes, reason });
export const unblockAddress = (address: string) => sendJson(`${BASE}/blocks/${encodeURIComponent(address)}`, 'DELETE');
export const confirmChange = () => sendJson(`${BASE}/confirm`, 'POST');
export const rollbackChange = () => sendJson(`${BASE}/rollback`, 'POST');
export const defend = (kind: string, target: string, minutes: number) =>
  sendJson<DefenseState>(`${BASE}/defense/actions`, 'POST', { kind, target, minutes, reason: 'manuale' });
export const revokeDefense = (key: string) => sendJson(`${BASE}/defense/responses/${encodeURIComponent(key)}`, 'DELETE');
export const showDefenseView = (open: boolean) => sendJson(`${BASE}/defense/view`, 'POST', { open });
export const refreshGeo = () => sendJson(`${BASE}/geo/refresh`, 'POST');
export const requestTrust = (address: string, label: string) => sendJson<TrustRequest>(`${BASE}/trusted/requests`, 'POST', { address, label });
export const confirmTrust = (id: string, code: string, acceptRisks: boolean) =>
  sendJson(`${BASE}/trusted/requests/${encodeURIComponent(id)}/confirm`, 'POST', { code, accept_risks: acceptRisks });
export const untrust = (address: string) => sendJson(`${BASE}/trusted/${encodeURIComponent(address)}`, 'DELETE');
