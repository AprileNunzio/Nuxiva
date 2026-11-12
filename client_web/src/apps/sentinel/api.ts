import { sendJson } from '../shared/http';
import type { NvrErase } from './types';

export const statusUrl='/api/sentinel/status';
export const summaryUrl=(day:string)=>`/api/sentinel/summary?day=${encodeURIComponent(day)}`;
export function eventsUrl(range:{from:number;to:number},groups:string[],lang:string,before?:[number,string]|null) {
  const query=new URLSearchParams({from_ms:String(range.from),to_ms:String(range.to),groups:groups.join(','),limit:'200',lang});
  if(before){query.set('before_at',String(before[0]));query.set('before_id',before[1]);}
  return `/api/sentinel/events?${query}`;
}
export const deleteRange=(range:{from:number;to:number})=>sendJson<{removed:number}>(`/api/sentinel/events?from_ms=${range.from}&to_ms=${range.to}`,'DELETE');
export const saveRetention=(retention:Record<string,number>)=>sendJson('/api/sentinel/retention','PUT',retention);
export const sweepNow=()=>sendJson('/api/sentinel/sweep','POST');
export const nvrPrivacyUrl='/api/nvr/privacy';
export const privacyOverviewUrl='/api/sentinel/privacy/overview';
export const saveNvrPrivacy=(body:Record<string,unknown>)=>sendJson('/api/nvr/privacy','PUT',body);
export const announceNotice=()=>sendJson('/api/nvr/notice/announce','POST');
export const findUrl=(q:string)=>`/api/nvr/find?${new URLSearchParams({q:q.trim().slice(0,300),limit:'30'})}`;
export const erasePerson=(slug:string,deleteSegments:boolean)=>sendJson<NvrErase>(`/api/nvr/privacy/person/${encodeURIComponent(slug)}/erase`,'POST',{delete_segments:deleteSegments});
export const exportPersonUrl=(slug:string)=>`/api/nvr/privacy/person/${encodeURIComponent(slug)}`;
