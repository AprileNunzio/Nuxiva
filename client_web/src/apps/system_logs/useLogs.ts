import { useEffect, useState } from 'react';
import { useOSApp, useWindowToolbar } from '../shared/kit';
import { useResource, useAction } from '../shared/useResource';
import { useAccess } from '../../app_shell/access/AccessProvider';
import { useWindowTopology } from '../../app_shell/WindowTopology';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { sourcesUrl, entriesUrl, exportLogs } from './api';
import type { LogCatalog, LogEntry, LogResult } from './types';

export function useLogs() {
  const os=useOSApp(), access=useAccess(), {t,lang}=useScopedI18n('apps/system_logs');
  const {snapshot}=useWindowTopology();
  const target=os.nodeId || (access.nodes.includes('*')?'local':access.nodes[0] || 'local');
  const [source,setSource]=useState('events');
  const [severity,setSeverity]=useState('all');
  const [minutes,setMinutes]=useState(60);
  const [search,setSearch]=useState('');
  const [live,setLive]=useState(true);
  const [selected,setSelected]=useState<LogEntry|null>(null);
  useEffect(()=>{const timer=setTimeout(()=>setSearch(os.searchQuery),300);return()=>clearTimeout(timer);},[os.searchQuery]);
  useEffect(()=>{setSource('events');setSelected(null);},[target]);
  const catalogUrl=sourcesUrl(target);
  const catalogResource=useResource<LogCatalog>(catalogUrl,30000);
  const catalog=catalogResource.dataUrl===catalogUrl?catalogResource.data:null;
  const params=new URLSearchParams({node_id:target,source,severity,minutes:String(minutes),limit:'500',query:search});
  const url=entriesUrl(params);
  const resource=useResource<LogResult>(url,live?5000:0);
  const result=resource.dataUrl===url?resource.data:null;
  const {busy,run}=useAction();
  const time=(value:number|null)=>value===null?t('unknown_time'):new Date(value*1000).toLocaleString(lang);
  const name=target==='local'?(catalog?.hostname || t('this_device')):snapshot?.neurons.find(node=>node.id===target)?.name || target;
  const managementId=target==='local'?catalog?.local_node_id:target;
  useWindowToolbar(id=>{if(id.startsWith('export_')&&!busy)void run(()=>exportLogs(params,id.slice(7)),'core_app_action_failed');});
  useEffect(()=>os.setStatus({itemCount:result?.entries.length || 0,connected:!!result&&!resource.error}),[result?.generated_at,resource.error,os.setStatus]);
  useEffect(()=>setSelected(null),[target,source,severity,minutes,search]);
  const permittedNodes=snapshot?.neurons.filter(node=>access.nodes.includes('*')||access.nodes.includes(node.id)) || [];
  const currentSelection=result?.entries.find(row=>row.id===selected?.id)||null;
  return {os,access,t,lang,target,source,setSource,severity,setSeverity,minutes,setMinutes,live,setLive,selected:currentSelection,setSelected,
    catalog,catalogResource,resource,result,busy,time,name,managementId,permittedNodes};
}
export type LogsModel=ReturnType<typeof useLogs>;
