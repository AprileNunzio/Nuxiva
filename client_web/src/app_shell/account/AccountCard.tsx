import React, { useEffect, useId, useRef, useState } from 'react';
import { ChevronRight, Globe2, LogOut, Monitor, Settings2, ShieldCheck, UserRound, X } from 'lucide-react';
import { useAccess } from '../access/AccessProvider';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { reportError } from '../../shared/errors/errorBus';
import './account.css';

export function AccountCard({user,onClose,onSettings,onSignOut}:{user:string;onClose:()=>void;onSettings:()=>void;onSignOut:()=>Promise<void>}) {
  const {t,lang}=useScopedI18n('app_shell/account');
  const access=useAccess();
  const [busy,setBusy]=useState(false);
  const card=useRef<HTMLElement>(null);
  const title=useId();
  useEffect(()=>{
    card.current?.focus();
    const outside=(event:PointerEvent)=>{if(!card.current?.contains(event.target as Node)&&!(event.target as Element).closest('.os-task-user'))onClose();};
    window.addEventListener('pointerdown',outside);
    return()=>window.removeEventListener('pointerdown',outside);
  },[onClose]);
  const close=()=>{onClose();document.querySelector<HTMLButtonElement>('.os-task-user')?.focus();};
  const role=access.ready&&!access.failed? t(`role_${access.role}`) : t(access.failed?'access_failed':'loading');
  return <section className="os-account-card" ref={card} role="dialog" aria-labelledby={title} tabIndex={-1} onKeyDown={event=>{if(event.key==='Escape'){event.stopPropagation();close();}}}>
    <header><span className="os-account-avatar"><UserRound/></span><div><small>{t('session')}</small><h2 id={title}>{user}</h2></div><button aria-label={t('close')} onClick={close}><X/></button></header>
    <div className="os-account-facts">
      <div><ShieldCheck/><span>{t('role')}<strong>{role.startsWith('role_')?access.role:role}</strong></span></div>
      <div><Monitor/><span>{t('devices')}<strong>{access.ready&&!access.failed?(access.nodes.includes('*')?t('all_devices'):t('device_count',{count:access.nodes.length})):t('unavailable')}</strong></span></div>
      <div><Globe2/><span>{t('language')}<strong>{lang.toLocaleUpperCase()}</strong></span></div>
    </div>
    {access.ready&&!access.failed&&<details><summary>{t('permissions')}<ChevronRight/></summary><ul>{access.capabilities.map(permission=><li key={permission}>{permission==='*'?t('all_permissions'):permission}</li>)}</ul></details>}
    <div className="os-account-actions"><button onClick={()=>{onSettings();onClose();}}><Settings2/>{t('settings')}<ChevronRight/></button><button className="os-account-signout" disabled={busy} onClick={()=>{setBusy(true);onSignOut().catch(cause=>reportError('logout_failed',cause)).finally(()=>setBusy(false));}}><LogOut/>{t(busy?'signing_out':'sign_out')}</button></div>
  </section>;
}
