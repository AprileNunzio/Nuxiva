import React, { useCallback, useEffect, useState } from 'react';
import { appRegistry } from './window_manager/registry';
import { useWindowStore, windowStore } from './window_manager/WindowStore';
import { OSWindowFrame } from './window_manager/OSWindowFrame';
import { getScopedString, useScopedI18n } from '../shared/i18n/useScopedI18n';
import { NotificationCenter } from './NotificationCenter';
import './webos.css';
import { useAuthenticatedSession } from '../features/auth_gate';
import { WindowTopologyProvider } from './WindowTopology';
import { OSIcon3D } from './OSIcon3D';
import { Taskbar } from './Taskbar';
import { AccessProvider } from './access/AccessProvider';
import { Calendar } from './calendar/Calendar';
import { AccountCard } from './account/AccountCard';
import { StartMenu } from './start/StartMenu';
import { useAssistantIdentity } from '../shared/identity/IdentityContext';
import { useDesktopShortcuts } from './desktopShortcuts';

export const AppShell: React.FC = () => {
  const { user, signOut } = useAuthenticatedSession();
  return <AccessProvider user={user}><WindowTopologyProvider><WebOSDesktop user={user} onSignOut={signOut} /></WindowTopologyProvider></AccessProvider>;
};

export function WebOSDesktop({ user, onSignOut }: { user: string; onSignOut: () => Promise<void> }) {
  const windows = useWindowStore();
  const assistant = useAssistantIdentity();
  const { t, lang } = useScopedI18n('app_shell');
  const [launcher, setLauncher] = useState(false);
  const closeLauncher=useCallback(()=>setLauncher(false),[]);
  const [userMenu,setUserMenu]=useState(false);
  const closeUserMenu=useCallback(()=>setUserMenu(false),[]);
  const [calendar, setCalendar] = useState(false);
  const [notifications, setNotifications] = useState(false);
  const [notificationCount, setNotificationCount] = useState(0);
  const [clock, setClock] = useState(new Date());
  const [context, setContext] = useState<{ x: number; y: number } | null>(null);
  useEffect(() => { const timer = setInterval(() => setClock(new Date()), 30000); return () => clearInterval(timer); }, []);
  useEffect(() => {
    const close = (event: KeyboardEvent) => { if (event.key === 'Escape') { setLauncher(false); setContext(null); setCalendar(false);setNotifications(false);setUserMenu(false); } };
    window.addEventListener('keydown', close); return () => window.removeEventListener('keydown', close);
  }, []);
  useEffect(() => { windowStore.activateWorkspace(user); return () => windowStore.releaseWorkspace(); }, [user]);
  const title = (app: typeof appRegistry[number]) => (app.id === 'explorer' ? assistant.name : getScopedString(app.scope, lang, 'title', app.name));
  const open = (appId: string, newInstance = false) => {
    windowStore.openWindow({
      appId,
      instanceKey: newInstance ? `instance-${Date.now()}` : undefined
    });
    setLauncher(false);
    setContext(null);
  };
  const { shortcuts, isDefault, unpin } = useDesktopShortcuts();
  const [iconContext, setIconContext] = useState<{ x: number; y: number; appId: string } | null>(null);
  return <div className="webos">
    <main className="os-workspace" onContextMenu={event => { if ((event.target as HTMLElement).closest('.os-window')) return; event.preventDefault(); const rect = event.currentTarget.getBoundingClientRect(); setIconContext(null); setContext({x:Math.min(event.clientX-rect.left,rect.width-220),y:Math.min(event.clientY-rect.top,rect.height-160)}); }}>
      <div className="os-wallpaper" aria-hidden="true"><span>Nuxiva</span><small>by NunzioTech</small></div>
      <div className="os-desktop" onClick={() => { setLauncher(false); setContext(null); setIconContext(null); }}>
        {shortcuts.map(app => (
          <button
            key={app.id}
            onClick={event => { event.stopPropagation(); setIconContext(null); open(app.id,event.shiftKey); }}
            onContextMenu={event => {
              event.preventDefault();
              event.stopPropagation();
              setContext(null);
              setIconContext({ x: event.clientX, y: event.clientY, appId: app.id });
            }}
          >
            <OSIcon3D name={app.name} source={app.iconUrl} size="lg" />
            <span>{title(app)}</span>
          </button>
        ))}
      </div>
      {windows.map(entry => <OSWindowFrame key={entry.id} entry={entry} />)}
      {context && <div className="os-context-menu" style={{left:Math.max(0,context.x),top:Math.max(0,context.y)}} role="menu">
        <button role="menuitem" onClick={() => { setLauncher(true); setContext(null); }}>{t('os_applications')}</button>
        <button role="menuitem" onClick={() => { open('features_hub'); setContext(null); }}>{t('os_settings')}</button>
        <button role="menuitem" onClick={() => { windows.forEach(w => windowStore.update(w.id,{minimized:true})); setContext(null); }}>{t('os_desktop')}</button>
      </div>}
      {iconContext && <div className="os-context-menu" style={{left:Math.max(0,iconContext.x),top:Math.max(0,iconContext.y)}} role="menu">
        <button role="menuitem" onClick={() => { open(iconContext.appId); setIconContext(null); }}>{t('open') || 'Apri'}</button>
        {!isDefault(iconContext.appId) && (
          <button role="menuitem" onClick={() => { unpin(iconContext.appId); setIconContext(null); }}>{t('remove_from_desktop') || 'Rimuovi dal Desktop'}</button>
        )}
      </div>}
    </main>
    <Taskbar user={user} windows={windows} shortcuts={shortcuts} launcher={launcher} onStart={()=>{setLauncher(v=>!v);setUserMenu(false);setCalendar(false);}} onOpen={open} clock={clock} calendar={calendar} onCalendar={()=>{setCalendar(v=>!v);setLauncher(false);setNotifications(false);setUserMenu(false);}} userMenu={userMenu} onUserMenu={()=>{setUserMenu(v=>!v);setLauncher(false);setCalendar(false);setNotifications(false);}} />
    {userMenu&&<AccountCard user={user} onClose={closeUserMenu} onSettings={()=>open('features_hub')} onSignOut={onSignOut}/>}
    {launcher&&<StartMenu user={user} windows={windows} onOpen={open} onClose={closeLauncher} onAccount={()=>{setLauncher(false);setUserMenu(true);}} onSettings={()=>open('features_hub')} onNotifications={()=>{setNotifications(true);setLauncher(false);}} notificationCount={notificationCount}/>}
    {calendar && <Calendar now={clock} onClose={()=>setCalendar(false)} />}
    <NotificationCenter visible={notifications} onClose={()=>setNotifications(false)} onCountChange={setNotificationCount} />

  </div>;
}
