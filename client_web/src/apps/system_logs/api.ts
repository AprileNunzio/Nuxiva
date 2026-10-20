import { download } from '../../shared/http/download';
export const sourcesUrl=(nodeId:string)=>`/api/v5/logs/sources?node_id=${encodeURIComponent(nodeId)}`;
export const entriesUrl=(parameters:URLSearchParams)=>`/api/v5/logs/entries?${parameters}`;
export function exportLogs(parameters:URLSearchParams,format:string) {
  return download(`/api/v5/logs/export?${parameters}&format=${format}`,`nuxiva-${format==='report'?'diagnostic-report':'logs'}-${Date.now()}.${format==='report'?'json':format}`);
}
