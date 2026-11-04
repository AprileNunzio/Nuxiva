import React, { useContext, useState, useEffect } from 'react';
import { Circle, RefreshCw, FileText, Network, ShieldCheck, Clock3, History, Settings2, Info } from 'lucide-react';
import { WindowContext } from './WindowContext';
import { resolveApp } from './registry';
import { windowStore } from './WindowStore';
import { getScopedString, useScopedI18n } from '../../shared/i18n/useScopedI18n';
import './application.css';

const symbols = { overview:RefreshCw, changes:FileText, network:Network, diagnostics:ShieldCheck, schedule:Clock3, history:History, settings:Settings2, info:Info };
/** Shared application chrome. Apps supply data-bound section content; manifests supply navigation. */
export function AppViewFrame({sections,parameters,loading,error,onRetry,contentClassName='',header,footer}:{
  sections:Record<string,React.ReactNode>;parameters?:Record<string,string|number>;
  loading?:boolean;error?:string;onRetry?:()=>void;contentClassName?:string;
  header?:React.ReactNode;footer?:React.ReactNode;
}) {
  const entry=useContext(WindowContext);
  const app=entry ? resolveApp(entry.appId) : undefined;
  const {lang,t}=useScopedI18n('app_shell');
  const [local,setLocal]=useState('');
  const navigation=app?.navigation?.filter(item=>Object.prototype.hasOwnProperty.call(sections,item.id)) || [];
  const requested=entry?.activeSection || local;
  const selected=Object.prototype.hasOwnProperty.call(sections,requested) ? requested : navigation[0]?.id || Object.keys(sections)[0];
  const [visited,setVisited]=useState<Set<string>>(()=>new Set([selected]));
  useEffect(()=>setVisited(previous=>previous.has(selected)?previous:new Set([...previous,selected])),[selected]);
  const label=(key:string)=>{let text=getScopedString(app?.scope || 'app_shell',lang,key,t(key));for(const [name,value] of Object.entries(parameters || {}))text=text.split(`{${name}}`).join(String(value));return text;};
  if(loading)return <div className="os-app-state" role="status">{t('os_loading')}</div>;
  if(error)return <div className="os-app-state" role="alert"><p>{error}</p>{onRetry&&<button onClick={onRetry}>{t('os_refresh')}</button>}</div>;
  return <div className="os-application-layout">
    {navigation.length>0&&<aside className="os-app-sidebar"><div className="os-app-identity"><strong>{label('title')}</strong>{app?.version&&<span>{app.version}</span>}</div><nav aria-label={label('title')}>{navigation.map(item=>{
      const Icon=symbols[item.icon as keyof typeof symbols] || Circle;
      return <button key={item.id} aria-label={label(item.labelKey)} title={label(item.labelKey)} aria-current={selected===item.id?'page':undefined} onClick={()=>entry ? windowStore.update(entry.id,{activeSection:item.id}) : setLocal(item.id)}><Icon aria-hidden="true"/><span>{label(item.labelKey)}</span></button>;
    })}</nav></aside>}
    <div className={`os-app-body ${contentClassName}`}>{header&&<div className="os-app-header">{header}</div>}{Object.entries(sections).filter(([id])=>id===selected||visited.has(id)).map(([id,content])=><div key={id} hidden={id!==selected}>{content}</div>)}{footer&&<div className="os-app-footer">{footer}</div>}</div>
  </div>;
}
