import React from 'react';
import { AppViewFrame, OSDataGrid } from '../shared/kit';
import { NodeConsoleView } from '../../node_apps/console/NodeConsoleView';
import { useLogs } from './useLogs';
import { Overview } from './Overview';
import { Records } from './Records';
import { Controls } from './Controls';
import './logs.css';

export function View() {
  const model=useLogs(), {t,catalog,name,managementId,access,os}=model;
  return <AppViewFrame header={<Controls model={model}/>} footer={<small className="logs-notice">{t('redaction_hint')}</small>} sections={{
    overview:<Overview model={model}/>,
    records:<Records model={model}/>,
    sources:<div><h1>{t('sources')}</h1><p className="logs-notice">{name}</p><p className="logs-notice">{t('source_scan_hint')}</p>
      <OSDataGrid rows={catalog?.sources || []} rowId={row=>row.id} emptyLabel={t('empty')} onSelect={item=>{model.setSource(item.id);os.setActiveTab('records');}} columns={[
        {id:'name',label:t('source'),sort:row=>row.name,value:row=>row.id==='journal'?t('kind_journal'):row.name},
        {id:'kind',label:t('kind'),sort:row=>row.kind,value:row=>t(`kind_${row.kind}`)},
        {id:'state',label:t('state'),value:row=>row.state?(t(`source_state_${row.state}`)===`source_state_${row.state}`?row.state:t(`source_state_${row.state}`)):t('available')},
      ]}/>{catalog?.warnings.map(warning=><p className="logs-notice" key={warning}>{t(warning)}</p>)}
    </div>,
    device:managementId&&access.can('api.admin')?<NodeConsoleView key={managementId} nodeId={managementId} initialName={name} onBack={()=>os.setActiveTab('overview')} onRenamed={()=>model.catalogResource.reload()} standaloneApps/>:<p>{t('device_unavailable')}</p>,
  }}/>;
}
