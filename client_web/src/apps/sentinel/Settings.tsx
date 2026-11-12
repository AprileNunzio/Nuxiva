import React, { useEffect, useState } from 'react';
import { deleteRange, saveRetention, sweepNow } from './api';
import type { SentinelModel } from './useSentinel';

const LIMITS:Record<string,number>={appearance:30,guest_appearance:7,denied:730,system:730,audit:730};

export function Settings({model:m}:{model:SentinelModel}) {
  const {t,status,run,busy}=m;
  const [draft,setDraft]=useState<Record<string,number>>({});
  const [note,setNote]=useState('');
  useEffect(()=>{if(status.data?.retention)setDraft(status.data.retention);},[status.data?.retention]);
  const save=async()=>{if(await run(()=>saveRetention(draft)))setNote(t('saved'));};
  const remove=async()=>{
    if(!window.confirm(t('delete_confirm')))return;
    const result=await run(()=>deleteRange(m.range));
    if(result)setNote(t('deleted',{count:result.removed}));
  };
  return <div className="sentinel-settings">
    <h2>{t('retention')}</h2><p className="sentinel-hint">{t('retention_hint')}</p>
    <div className="sentinel-retention">{Object.entries(draft).map(([group,days])=><label key={group}><span>{t(`ret_${group}`)}</span>
      <input type="number" min={1} max={LIMITS[group]||365} value={days} onChange={e=>setDraft({...draft,[group]:Math.max(1,Math.min(LIMITS[group]||365,Number(e.target.value)||1))})}/><small>{t('days')}</small></label>)}</div>
    <div className="sentinel-actions">
      <button disabled={busy||!Object.keys(draft).length} onClick={()=>void save()}>{t('save')}</button>
      <button disabled={busy} onClick={()=>void run(sweepNow)}>{t('sweep')}</button>
      <button className="danger" disabled={busy} onClick={()=>void remove()}>{t('delete_day')}</button>
    </div>
    {note&&<p role="status" className="sentinel-hint">{note}</p>}
    <p className="sentinel-hint">{t('audit_hint')}</p>
  </div>;
}
