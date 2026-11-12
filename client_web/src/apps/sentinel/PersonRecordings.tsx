import React, { useState } from 'react';
import { Download, Eraser } from 'lucide-react';
import { getJson } from '../shared/http';
import { useResource } from '../shared/useResource';
import { erasePerson, exportPersonUrl, privacyOverviewUrl } from './api';
import type { PrivacyProfile } from './types';
import type { SentinelModel } from './useSentinel';

function download(name:string,data:unknown){
  const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));
  const a=document.createElement('a');a.href=url;a.download=name;a.rel='noopener';a.click();
  window.setTimeout(()=>URL.revokeObjectURL(url),1000);
}

export function PersonRecordings({model:m}:{model:SentinelModel}) {
  const {t,busy,run}=m;
  const res=useResource<{profiles:PrivacyProfile[]}>(privacyOverviewUrl,0);
  const [slug,setSlug]=useState('');
  const [clips,setClips]=useState(false);
  const [note,setNote]=useState('');
  const profiles=res.data?.profiles||[];
  const person=profiles.find(p=>p.slug===slug);
  const exportNow=async()=>{const data=await run(()=>getJson<{turns:unknown[]}>(exportPersonUrl(slug)));if(data){download(`nuxiva-registrazioni-${slug}.json`,data);setNote(t('nvr_exported',{count:data.turns.length}));}};
  const erase=async()=>{
    if(!person||!window.confirm(t(clips?'nvr_erase_confirm_clips':'nvr_erase_confirm',{name:person.name})))return;
    const out=await run(()=>erasePerson(slug,clips));
    if(out)setNote(t('nvr_erased',{turns:out.turns_removed,segments:out.segments_deleted}));
  };
  return <section className="sentinel-nvr-block" aria-label={t('nvr_person')}>
    <h2>{t('nvr_person')}</h2><p className="sentinel-hint">{t('nvr_person_hint')}</p>
    <label className="sentinel-nvr-field wide"><span>{t('nvr_person_pick')}</span><select value={slug} onChange={e=>{setSlug(e.target.value);setNote('');}}>
      <option value="">—</option>{profiles.map(p=><option key={p.slug} value={p.slug}>{p.name}</option>)}
    </select></label>
    {person&&<p className="sentinel-hint">{person.consent_voice?t('nvr_voice_consent_yes'):t('nvr_voice_consent_no')}</p>}
    <label className="sentinel-nvr-switch"><input type="checkbox" checked={clips} onChange={e=>setClips(e.target.checked)}/><span>{t('nvr_erase_clips')}</span></label>
    <div className="sentinel-actions">
      <button disabled={busy||!slug} onClick={()=>void exportNow()}><Download aria-hidden="true"/>{t('nvr_export')}</button>
      <button className="danger" disabled={busy||!slug} onClick={()=>void erase()}><Eraser aria-hidden="true"/>{t('nvr_erase')}</button>
    </div>
    {note&&<p role="status" className="sentinel-hint">{note}</p>}
  </section>;
}
