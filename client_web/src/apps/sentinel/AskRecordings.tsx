import React, { useState } from 'react';
import { MessageSquareText, Search, Sparkles } from 'lucide-react';
import { getJson } from '../shared/http';
import { findUrl } from './api';
import type { NvrFind } from './types';
import type { SentinelModel } from './useSentinel';

export function AskRecordings({model:m}:{model:SentinelModel}) {
  const {t,lang,busy,run}=m;
  const [q,setQ]=useState('');
  const [result,setResult]=useState<NvrFind|null>(null);
  const submit=async(e:React.FormEvent)=>{e.preventDefault();if(!q.trim())return;const found=await run(()=>getJson<NvrFind>(findUrl(q)));if(found)setResult(found);};
  const when=(ms:number)=>new Date(ms).toLocaleString(lang,{weekday:'short',day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'});
  const hits=result?[...result.speech,...result.events].sort((a,b)=>b.at_ms-a.at_ms):[];
  return <section className="sentinel-nvr-block" aria-label={t('nvr_ask')}>
    <h2>{t('nvr_ask')}</h2><p className="sentinel-hint">{t('nvr_ask_hint')}</p>
    <form className="sentinel-nvr-ask" role="search" onSubmit={e=>void submit(e)}>
      <Search aria-hidden="true"/><input type="search" maxLength={300} value={q} onChange={e=>setQ(e.target.value)} placeholder={t('nvr_ask_placeholder')} aria-label={t('nvr_ask')}/>
      <button disabled={busy||!q.trim()}>{t('nvr_ask_go')}</button>
    </form>
    {result&&(hits.length?<ol className="sentinel-nvr-hits" aria-live="polite">{hits.map((h,i)=><li key={`${h.kind}-${h.camera}-${h.at_ms}-${i}`}>
      {h.kind==='speech'?<MessageSquareText aria-hidden="true"/>:<Sparkles aria-hidden="true"/>}
      <div><small>{when(h.at_ms)} · {result.cameras[h.camera]?.name||h.camera} · {h.kind==='speech'?(h.speaker_name||h.speaker||h.voice||t('nvr_unknown_voice')):t(`nvr_kind_${h.kind}`)}</small><p>{h.text||t(`nvr_kind_${h.kind}`)}</p></div>
    </li>)}</ol>:<p className="sentinel-hint">{t('nvr_ask_none')}</p>)}
  </section>;
}
