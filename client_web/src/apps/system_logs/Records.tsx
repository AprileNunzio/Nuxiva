import React from 'react';
import { X } from 'lucide-react';
import { OSDataGrid } from '../shared/kit';
import type { LogEntry } from './types';
import type { LogsModel } from './useLogs';

export function Records({model:m}:{model:LogsModel}) {
  const {t,result,name,selected,setSelected,time}=m;
  return <div><h1>{t('records')}</h1><p className="logs-notice">{name}</p>
    {m.catalog?.scope==='server_events_only'&&<p className="logs-notice">{t('remote_limit')}</p>}
    {!result?<p role="status">{t(m.resource.error?'unreachable':'loading')}</p>:<>
      <p className="logs-sample">{t('sample',{count:result.entries.length})} · {new Date(result.generated_at).toLocaleString(m.lang)}{result.limit_reached?` · ${t('limit_reached')}`:''}</p>
      <OSDataGrid<LogEntry> rows={result.entries} rowId={row=>row.id} emptyLabel={t('empty')} onSelect={setSelected} columns={[
        {id:'time',label:t('time'),sort:row=>row.timestamp||0,value:row=>time(row.timestamp)},
        {id:'severity',label:t('severity'),sort:row=>row.severity,value:row=><span className="log-level" data-level={row.severity}>{t(`severity_${row.severity}`)}</span>},
        {id:'source',label:t('source'),sort:row=>row.source,value:row=>row.source},
        {id:'message',label:t('message'),value:row=><span className="log-message">{row.message}</span>},
      ]}/>
    </>}
    {selected&&<aside className="logs-inspector"><header><strong>{t('details')}</strong><button aria-label={t('close')} onClick={()=>setSelected(null)}><X/></button></header><p>{time(selected.timestamp)} · {selected.source} · {t(`severity_source_${selected.severity_source}`)}</p><pre>{selected.message}</pre></aside>}
  </div>;
}
