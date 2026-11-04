import React from 'react';
import { Pause, Play, Download } from 'lucide-react';
import type { LogsModel } from './useLogs';

export function Controls({model:m}:{model:LogsModel}) {
  const {t,lang,target,source,catalog,minutes,severity,live}=m;
  return <div><div className="logs-controls">
    <label>{t('device')}<select value={target} onChange={event=>m.os.setNodeId(event.target.value)}>
      {m.access.nodes.includes('*')&&<option value="local">{catalog?.hostname || t('this_device')}</option>}
      {!m.permittedNodes.some(node=>node.id===target)&&target!=='local'&&<option value={target}>{target}</option>}
      {m.permittedNodes.filter(node=>node.id!==catalog?.local_node_id||target!=='local').map(node=><option key={node.id} value={node.id}>{node.name}</option>)}
    </select></label>
    <label>{t('source')}<select value={source} onChange={event=>m.setSource(event.target.value)}>{(catalog?.sources || [{id:'events',name:'Nuxiva'}]).map(item=><option key={item.id} value={item.id}>{item.id==='journal'?t('kind_journal'):item.name}</option>)}</select></label>
    <label>{t('period')}<select value={minutes} onChange={event=>m.setMinutes(Number(event.target.value))}>{[15,60,360,1440,10080,43200].map(value=><option key={value} value={value}>{new Intl.RelativeTimeFormat(lang,{numeric:'always'}).format(-value/(value<60?1:value<1440?60:1440),value<60?'minute':value<1440?'hour':'day')}</option>)}</select></label>
    <label>{t('severity')}<select value={severity} onChange={event=>m.setSeverity(event.target.value)}>{['all','error','warning','info','debug'].map(level=><option key={level} value={level}>{t(`severity_${level}`)}</option>)}</select></label>
    <button aria-pressed={live} onClick={()=>m.setLive(value=>!value)}>{live?<Pause aria-hidden="true"/>:<Play aria-hidden="true"/>}{t(live?'pause':'resume')}</button>
    {m.busy&&<span className="logs-notice" role="status"><Download aria-hidden="true"/>{t('exporting')}</span>}
  </div>{(m.resource.error||m.catalogResource.error)&&<p className="logs-alert" role="alert">{t('unreachable')} {m.result&&t('stale_hint')}</p>}</div>;
}
