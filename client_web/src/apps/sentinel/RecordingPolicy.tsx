import React, { useEffect, useState } from 'react';
import { Lock, Mic, MicOff, Volume2 } from 'lucide-react';
import { useResource } from '../shared/useResource';
import { announceNotice, nvrPrivacyUrl, saveNvrPrivacy } from './api';
import type { NvrPrivacy } from './types';
import type { SentinelModel } from './useSentinel';

export function RecordingPolicy({model:m}:{model:SentinelModel}) {
  const {t,lang,busy,run}=m;
  const res=useResource<NvrPrivacy>(nvrPrivacyUrl,30000), data=res.data;
  const [rooms,setRooms]=useState('');
  const [note,setNote]=useState('');
  useEffect(()=>{if(data)setRooms(data.private_rooms.join(', '));},[data?.private_rooms.join('|')]);
  const save=async(body:Record<string,unknown>)=>{if(await run(()=>saveNvrPrivacy(body))){res.reload();setNote(t('saved'));}};
  const toggle=(camera:string,on:boolean)=>{if(!data)return;const set=new Set(data.cameras.filter(c=>c.opted_in).map(c=>c.camera));if(on)set.add(camera);else set.delete(camera);void save({audio_cameras:[...set]});};
  const announce=async()=>{if(await run(announceNotice)){res.reload();setNote(t('nvr_notice_sent'));}};
  if(!data)return <p className="sentinel-hint">{res.error?t('unreachable'):t('loading')}</p>;
  const last=data.notice.last_spoken_ms?new Date(data.notice.last_spoken_ms).toLocaleString(lang):t('nvr_never');
  return <>
    <section className="sentinel-nvr-block" aria-label={t('nvr_notice')}>
      <h2>{t('nvr_notice')}</h2><p className="sentinel-hint">{t('nvr_notice_hint')}</p>
      <label className="sentinel-nvr-switch"><input type="checkbox" checked={data.notice_enabled} disabled={busy} onChange={e=>void save({notice_enabled:e.target.checked})}/><span>{t('nvr_notice_enabled')}</span></label>
      <label className="sentinel-nvr-field"><span>{t('nvr_notice_repeat')}</span><input type="number" min={1} max={168} defaultValue={data.notice_repeat_hours} onBlur={e=>void save({notice_repeat_hours:Math.max(1,Math.min(168,Number(e.target.value)||12))})}/><small>{t('nvr_hours')}</small></label>
      <p className="sentinel-hint">{data.recording_audio.length?t('nvr_notice_places',{places:data.notice.places.join(', ')||'-'}):t('nvr_no_audio')} · {t('nvr_notice_last',{when:last})}{data.notice.pending?` · ${t('nvr_notice_pending')}`:''}</p>
      <div className="sentinel-actions"><button disabled={busy||!data.notice_enabled||!data.recording_audio.length} onClick={()=>void announce()}><Volume2 aria-hidden="true"/>{t('nvr_notice_now')}</button></div>
    </section>
    <section className="sentinel-nvr-block" aria-label={t('nvr_audio')}>
      <h2>{t('nvr_audio')}</h2><p className="sentinel-hint">{t('nvr_audio_hint')}</p>
      {data.cameras.length===0?<p className="sentinel-hint">{t('nvr_no_cameras')}</p>:<ul className="sentinel-nvr-cams">{data.cameras.map(c=><li key={c.camera} data-allowed={c.allowed}>
        {c.private?<Lock aria-hidden="true"/>:c.allowed?<Mic aria-hidden="true"/>:<MicOff aria-hidden="true"/>}
        <div><strong>{c.name}</strong><small>{c.room||t('nvr_no_room')} · {t(`nvr_reason_${c.reason}`)}</small></div>
        <label className="sentinel-nvr-switch"><input type="checkbox" checked={c.opted_in&&!c.private} disabled={busy||c.private} onChange={e=>toggle(c.camera,e.target.checked)}/><span>{t('nvr_audio_on')}</span></label>
      </li>)}</ul>}
      <label className="sentinel-nvr-field wide"><span>{t('nvr_private_rooms')}</span><input value={rooms} maxLength={1500} onChange={e=>setRooms(e.target.value)} onBlur={()=>void save({private_rooms:rooms.split(',').map(r=>r.trim()).filter(Boolean).slice(0,50)})} placeholder={t('nvr_private_rooms_placeholder')}/></label>
      {note&&<p role="status" className="sentinel-hint">{note}</p>}
    </section>
  </>;
}
