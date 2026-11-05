import { sendJson } from '../shared/http';

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
