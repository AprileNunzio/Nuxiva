import { sendJson } from '../../shared/http';

export type Verdict = 'accept' | 'reject' | 'snooze';

export const decide = (id: string, verdict: Verdict) => sendJson<{ message: string }>(`/api/habits/${encodeURIComponent(id)}`, 'POST', { verdict });
export const analyse = () => sendJson<{ found: number }>('/api/habits/analyse', 'POST');
