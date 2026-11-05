import React, { useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { useResource } from '../shared/useResource';
import { sendJson } from '../shared/http';
import { statusUrl } from './api';
import type { SentinelStatus } from './types';

const STAGES=new Set(['wheel','egress','netguard','agency','display','done']);

export function NativeGate({t,children}:{t:(key:string,params?:Record<string,string|number>)=>string;children:React.ReactNode}) {
  const status=useResource<SentinelStatus>(statusUrl,10000);
  const [asked,setAsked]=useState(false);
  const [failed,setFailed]=useState(false);
  if(!status.data)return status.error?<p className="sentinel-empty" role="alert">{t('unreachable')}</p>:<p className="sentinel-empty" role="status">{t('loading')}</p>;
  if(status.data.native)return <>{children}</>;
  const build=status.data.build||{state:'unknown',stage:null,at:null};
  const stage=build.stage&&STAGES.has(build.stage)?t(`native_stage_${build.stage}`):'';
  const state=['building','failed','disabled'].includes(build.state)?build.state:'missing';
  const rebuild=async()=>{
    setFailed(false);
    try{await sendJson('/api/actions/rerun-step','POST',{step:'native'});setAsked(true);status.reload();}
    catch(error){console.warn('Compilazione del modulo nativo non avviata',error);setFailed(true);}
  };
  return <div className="sentinel-native" role="status" aria-live="polite">
    <p className="sentinel-native-title">{t(`native_${state}`)}</p>
    {state==='building'&&stage&&<p className="sentinel-native-detail">{t('native_stage',{stage})}</p>}
    {state==='building'&&<p className="sentinel-native-detail">{t('native_auto_open')}</p>}
    {(state==='failed'||state==='missing')&&<button type="button" className="sentinel-native-action" onClick={rebuild} disabled={asked}>
      <RefreshCw size={14} aria-hidden="true"/>{t(asked?'native_requested':'native_rebuild')}</button>}
    {failed&&<p className="sentinel-native-detail" role="alert">{t('native_rebuild_failed')}</p>}
  </div>;
}
