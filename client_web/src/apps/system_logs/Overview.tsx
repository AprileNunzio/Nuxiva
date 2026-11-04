import React from 'react';
import { AlertOctagon, TriangleAlert, Info, Bug, Activity, ShieldCheck } from 'lucide-react';
import { OSMetricCard } from '../shared/kit';
import type { LogsModel } from './useLogs';

export function Overview({model:m}:{model:LogsModel}) {
  const {t,result,name,lang,minutes}=m;
  if(!result)return <p role="status">{t(m.resource.error?'unreachable':'loading')}</p>;
  const finish=new Date(result.generated_at).getTime()/1000;
  const duration=minutes*60, bins=Array<number>(16).fill(0);
  for(const entry of result.entries)if(entry.timestamp!==null) {
    const index=Math.floor((entry.timestamp-(finish-duration))/duration*bins.length);
    if(index>=0&&index<bins.length)bins[index]++;
  }
  const maximum=Math.max(1,...bins);
  const metrics=[{id:'error',icon:<AlertOctagon/>,tone:'red' as const},{id:'warning',icon:<TriangleAlert/>,tone:'amber' as const},
    {id:'info',icon:<Info/>,tone:'blue' as const},{id:'debug',icon:<Bug/>,tone:'violet' as const}];
  return <div className="logs-overview">
    <div className="logs-heading"><div><p className="logs-eyebrow">{t('technical_analysis')}</p><h1>{name}</h1></div><span className="logs-live" data-live={m.live&&!m.resource.error}><span/>{t(m.resource.error?'disconnected':m.live?'live':'paused')}</span></div>
    <p className="logs-notice">{t('scope_hint')}</p>
    <div className="logs-summary">{metrics.map(metric=><OSMetricCard key={metric.id} label={t(`severity_${metric.id}`)} value={result.counts[metric.id]||0} icon={metric.icon} tone={metric.tone}/>)}</div>
    <figure className="logs-activity"><figcaption><Activity aria-hidden="true"/>{t('activity')}<span>{t('sample',{count:result.entries.length})}</span></figcaption><div className="logs-chart" role="img" aria-label={t('activity')}>
      {bins.map((count,index)=>{const at=new Date((finish-duration+duration*index/bins.length)*1000).toLocaleString(lang);return <div key={index} title={`${at} · ${t('occurrences',{count})}`}><span style={{height:`${count/maximum*100}%`}}/></div>;})}
    </div><div className="logs-chart-axis"><span>{new Date((finish-duration)*1000).toLocaleString(lang)}</span><span>{new Date(finish*1000).toLocaleString(lang)}</span></div></figure>
    <div className="logs-state"><ShieldCheck aria-hidden="true"/><div><strong>{t('machine_phase')}</strong><span>{result.phase || t('unknown_state')}</span></div><time dateTime={result.generated_at}>{new Date(result.generated_at).toLocaleString(lang)}</time></div>
    {result.analysis.length?result.analysis.map(issue=><section className="logs-finding" key={issue.code}><h2><TriangleAlert aria-hidden="true"/>{t(`analysis_${issue.code}`)}</h2><p>{t(`advice_${issue.code}`)}</p><small>{t('occurrences',{count:issue.occurrences})}</small></section>):<p className="logs-notice">{t(result.entries.length?'no_patterns':'empty')}</p>}
    {result.scope==='server_events_only'&&<p className="logs-notice">{t('remote_limit')}</p>}
    {result.untimed_count>0&&<p className="logs-notice">{t('untimed_hint',{count:result.untimed_count})}</p>}
    {result.limit_reached&&<p className="logs-notice">{t('limit_reached')}</p>}
  </div>;
}
