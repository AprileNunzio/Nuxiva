import { useEffect, useMemo, useState } from 'react';
import { useOSApp, useWindowToolbar } from '../shared/kit';
import { useResource, useAction } from '../shared/useResource';
import { getJson } from '../shared/http';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { eventsUrl, statusUrl, summaryUrl } from './api';
import type { SentinelEvent, SentinelPage, SentinelStatus, SentinelSummary } from './types';

const today=()=>{const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;};
const bounds=(day:string)=>{const start=new Date(`${day}T00:00:00`).getTime();return {from:start,to:start+86_399_999};};

export function useSentinel() {
  const os=useOSApp(), {t,lang}=useScopedI18n('apps/sentinel');
  const [day,setDay]=useState(today());
  const [extra,setExtra]=useState<SentinelEvent[]>([]);
  const [next,setNext]=useState<[number,string]|null>(null);
  const range=useMemo(()=>bounds(day),[day]);
  const language=lang.slice(0,2);
  const status=useResource<SentinelStatus>(statusUrl,60000);
  const url=eventsUrl(range,[],language);
  const page=useResource<SentinelPage>(url,day===today()?15000:0);
  const summary=useResource<SentinelSummary>(summaryUrl(day),day===today()?60000:0);
  const {busy,run}=useAction(()=>{page.reload();summary.reload();status.reload();});
  useEffect(()=>{setExtra([]);setNext(null);},[url]);
  useEffect(()=>{if(page.dataUrl===url)setNext(page.data?.next||null);},[page.data,page.dataUrl,url]);
  useWindowToolbar(id=>{if(id==='refresh'){page.reload();summary.reload();status.reload();}});
  const query=os.searchQuery.trim().toLocaleLowerCase(lang);
  const events=[...(page.dataUrl===url?page.data?.events||[]:[]),...extra].filter(e=>!query||e.text.toLocaleLowerCase(lang).includes(query));
  useEffect(()=>os.setStatus({itemCount:events.length,connected:!page.error}),[events.length,page.error,os.setStatus]);
  const more=async()=>{
    if(!next)return;
    const result=await run(()=>getJson<SentinelPage>(eventsUrl(range,[],language,next)));
    if(result){setExtra(previous=>[...previous,...result.events]);setNext(result.next);}
  };
  const time=(ms:number)=>new Date(ms).toLocaleTimeString(lang,{hour:'2-digit',minute:'2-digit'});
  return {t,lang,day,setDay,range,status,page,summary,events,more,hasMore:!!next,busy,run,time};
}
export type SentinelModel=ReturnType<typeof useSentinel>;
