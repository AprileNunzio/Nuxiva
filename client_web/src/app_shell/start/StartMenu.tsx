import React, { useEffect, useRef, useState } from 'react';
import { Bell, ChevronRight, CircleDot, Grid2X2, Layers, Search, Settings2, Shield, UserRound, X } from 'lucide-react';
import { appRegistry } from '../window_manager/registry';
import type { OSWindow } from '../window_manager/types';
import { useScopedI18n, getScopedString } from '../../shared/i18n/useScopedI18n';
import { sortByLocalizedLabel } from '../../shared/i18n/sortByLocalizedLabel';
import { OSIcon3D } from '../OSIcon3D';
import { useAccess } from '../access/AccessProvider';
import { useAssistantIdentity } from '../../shared/identity/IdentityContext';
import './start.css';

export function StartMenu({user,windows,onOpen,onClose,onAccount,onSettings,onNotifications,notificationCount}:{
  user:string;windows:OSWindow[];onOpen:(id:string,newInstance?:boolean)=>void;onClose:()=>void;
  onAccount:()=>void;onSettings:()=>void;onNotifications:()=>void;notificationCount:number;
}) {
  const {t,lang}=useScopedI18n('app_shell/start');
  const shell=useScopedI18n('app_shell');
  const access=useAccess();
  const assistant=useAssistantIdentity();
  const panel=useRef<HTMLElement>(null);
  const [search,setSearch]=useState('');
  const [category,setCategory]=useState('all');
  const apps=appRegistry.filter(app=>app.launcher!==false);
  const title=(app:typeof apps[number])=>(app.id === 'explorer' ? assistant.name : getScopedString(app.scope,lang,'title',app.name));
  const categoryTitle=(id:string)=>{const label=shell.t(`os_category_${id}`);return label.startsWith('os_category_')?id:label;};
  const categories=[...new Set(apps.map(app=>app.category||'system'))].sort((a,b)=>categoryTitle(a).localeCompare(categoryTitle(b),lang));
  const normalize=(text:string)=>text.normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase(lang);
  const filtered=sortByLocalizedLabel(apps.filter(app=>(category==='all'||(app.category||'system')===category)&&normalize(`${title(app)} ${app.name}`).includes(normalize(search))),lang,title);
  const allowed=(app:typeof apps[number])=>access.ready&&!access.failed&&(app.capabilities?.length?app.capabilities:['api.admin']).every(access.can);
  const running=new Set(windows.map(entry=>entry.appId));
  const activeIds=[...new Set([...windows].sort((a,b)=>b.z-a.z).map(entry=>entry.appId))];
  const recent=activeIds.map(id=>apps.find(app=>app.id===id)).filter((app):app is typeof apps[number]=>!!app).slice(0,6);
  useEffect(()=>{
    const outside=(event:PointerEvent)=>{if(!panel.current?.contains(event.target as Node)&&!(event.target as Element).closest('[data-os-start]'))onClose();};
    window.addEventListener('pointerdown',outside);
    return()=>window.removeEventListener('pointerdown',outside);
  },[onClose]);
  function application(app:typeof apps[number],compact=false) {
    return <button key={app.id} className={compact?'os-start-recent':'os-start-app'} disabled={!allowed(app)} title={allowed(app)?title(app):t('restricted')} onClick={event=>onOpen(app.id,event.shiftKey)}>
      <OSIcon3D name={app.name} source={app.iconUrl}/><span>{title(app)}</span>{running.has(app.id)&&<i aria-label={t('running')}/>}{!allowed(app)&&<Shield className="os-start-lock"/>}
    </button>;
  }
  return <section ref={panel} className="os-start-menu" role="dialog" aria-label={t('applications')} onKeyDown={event=>{if(event.key==='Escape'){event.stopPropagation();onClose();document.querySelector<HTMLButtonElement>('[data-os-start]')?.focus();}}}>
    <header><div><strong>Nuxiva</strong><small>by NunzioTech</small></div><button aria-label={t('close')} onClick={onClose}><X/></button></header>
    <label className="os-start-search"><Search/><input autoFocus value={search} aria-label={t('search')} placeholder={t('search')} onChange={event=>setSearch(event.target.value)}/>{search&&<button aria-label={t('clear')} onClick={()=>setSearch('')}><X/></button>}</label>
    <div className="os-start-main"><nav aria-label={t('categories')}><button aria-pressed={category==='all'} onClick={()=>setCategory('all')}><Grid2X2/><span>{t('all')}</span><small>{apps.length}</small></button>{categories.map(id=><button key={id} aria-pressed={category===id} onClick={()=>setCategory(id)}><Layers/><span>{categoryTitle(id)}</span><small>{apps.filter(app=>(app.category||'system')===id).length}</small></button>)}</nav>
      <div className="os-start-results">{!search&&category==='all'&&recent.length>0&&<section className="os-start-active"><h3><CircleDot/>{t('running')}</h3><div>{recent.map(app=>application(app,true))}</div></section>}
        <div className="os-start-section-title"><h3>{category==='all'?t('applications'):categoryTitle(category)}</h3><span>{filtered.length}</span></div>
        {filtered.length?<div className="os-start-apps">{filtered.map(app=>application(app))}</div>:<div className="os-start-empty"><Search/><strong>{t('no_results')}</strong><p>{t('search_hint')}</p></div>}
      </div></div>
    <footer><button className="os-start-account" onClick={onAccount}><UserRound/><span>{user}</span><ChevronRight/></button><div><button title={t('settings')} aria-label={t('settings')} onClick={onSettings}><Settings2/></button><button title={t('notifications')} aria-label={t('notifications')} onClick={onNotifications}><Bell/>{notificationCount>0&&<span className="os-start-notification-count">{notificationCount}</span>}</button></div></footer>
  </section>;
}
