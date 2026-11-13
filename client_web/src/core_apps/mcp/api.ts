import { sendJson } from '../shared/http';

export const approveTool = (toolId: string) => sendJson(`/api/mcp/tools/${encodeURIComponent(toolId)}/approve`, 'POST');
