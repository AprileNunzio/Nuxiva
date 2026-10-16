import { sendJson } from '../shared/http';
import { FirewallRule, RuleDraft } from './types';

const BASE = '/api/firewall';

export const savePolicy = (change: Readonly<Record<string, unknown>>) => sendJson(`${BASE}/policy`, 'PUT', change);
export const addRule = (draft: RuleDraft) => sendJson(`${BASE}/rules`, 'POST', draft);
export const toggleRule = (rule: FirewallRule, enabled: boolean) => sendJson(`${BASE}/rules/${encodeURIComponent(rule.id)}`, 'PUT', { ...rule, enabled });
export const deleteRule = (id: string) => sendJson(`${BASE}/rules/${encodeURIComponent(id)}`, 'DELETE');
export const blockAddress = (address: string, minutes: number, reason: string) => sendJson(`${BASE}/blocks`, 'POST', { address, minutes, reason });
export const unblockAddress = (address: string) => sendJson(`${BASE}/blocks/${encodeURIComponent(address)}`, 'DELETE');
export const confirmChange = () => sendJson(`${BASE}/confirm`, 'POST');
export const rollbackChange = () => sendJson(`${BASE}/rollback`, 'POST');
