import React from 'react';
import { ShieldCheck, ShieldAlert } from 'lucide-react';
import type { SentinelModel } from './useSentinel';

export function Header({model:m}:{model:SentinelModel}) {
  const {t,summary}=m, info=summary.data, integrity=info?.integrity;
  const state=!integrity?null:integrity.signed===false?'bad':integrity.signed?'ok':'unsigned';
  return <div className="sentinel-header">
    <label><span>{t('day')}</span><input type="date" value={m.day} max={new Date().toISOString().slice(0,10)} onChange={e=>e.target.value&&m.setDay(e.target.value)}/></label>
    {info&&<span className="sentinel-chip">{t('events_count',{count:info.total})}</span>}
    {info&&<span className="sentinel-chip">{t('guests_count',{count:info.guests})}</span>}
    {state&&<span className="sentinel-integrity" data-state={state}>{state==='bad'?<ShieldAlert aria-hidden="true"/>:<ShieldCheck aria-hidden="true"/>}{t(`integrity_${state}`)}</span>}
    {integrity?.torn&&<span className="sentinel-integrity" data-state="bad">{t('torn')}</span>}
  </div>;
}
