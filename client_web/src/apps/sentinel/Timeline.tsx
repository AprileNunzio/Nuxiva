import React from 'react';
import { Eye, UserRound, Users, ShieldAlert, Bot, Monitor, Activity, BookOpen, Mic, KeyRound, type LucideIcon } from 'lucide-react';
import type { SentinelEvent } from './types';
import type { SentinelModel } from './useSentinel';

const ICONS:Record<string,LucideIcon>={presence:UserRound,appearance:Eye,guest:Users,voice:Mic,access:KeyRound,automation:Bot,self:Activity,display:Monitor,system:ShieldAlert,sentinel:BookOpen};

export function Timeline({model:m,groups}:{model:SentinelModel;groups?:string[]}) {
  const {t,events,time}=m;
  if(!m.page.data&&!m.page.error)return <p role="status">{t('loading')}</p>;
  if(m.page.error)return <p role="alert">{t('unreachable')}</p>;
  const shown=groups?events.filter(e=>groups.includes(e.group)):events;
  if(!shown.length)return <p className="sentinel-empty">{t('empty')}</p>;
  const hours=new Map<string,SentinelEvent[]>();
  for(const event of shown){const hour=new Date(event.at_ms).toLocaleTimeString(m.lang,{hour:'2-digit'});hours.set(hour,[...(hours.get(hour)||[]),event]);}
  return <div className="sentinel-timeline">
    {[...hours].map(([hour,list])=><section key={hour} className="sentinel-hour"><h3>{hour}</h3><ol>
      {list.map(event=>{const Icon=ICONS[event.group]||Activity;return <li key={event.id} className="sentinel-event" data-group={event.group} data-kind={event.kind}>
        <span className="sentinel-icon"><Icon aria-hidden="true"/></span>
        <div><p>{event.text}</p><small><time dateTime={new Date(event.at_ms).toISOString()}>{time(event.at_ms)}</time> · {t(`group_${event.group}`)}</small></div>
      </li>;})}
    </ol></section>)}
    {m.hasMore&&<button className="sentinel-more" disabled={m.busy} onClick={()=>void m.more()}>{t('more')}</button>}
  </div>;
}
