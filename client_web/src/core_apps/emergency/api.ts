import { sendJson } from '../shared/http';

export const testAlert = () => sendJson('/api/redalert/test', 'POST');
export const stopAlert = () => sendJson('/api/redalert/stop', 'POST');
