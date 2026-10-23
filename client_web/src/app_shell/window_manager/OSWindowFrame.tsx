import React, { Suspense, useState } from 'react';
import { useScopedI18n, getScopedString } from '../../shared/i18n/useScopedI18n';
import { resolveApp } from './registry';
import { windowStore } from './WindowStore';
import { WindowContext, WindowRuntimeProvider, useOSApp } from './WindowContext';
import type { OSWindow, WindowMode, ToolbarItem } from './types';
import { ManifestIcon } from './ManifestIcon';
import { ActionConfirmation } from './ActionConfirmation';
import { useWindowTopology } from '../WindowTopology';
import { useNodeControl } from '../../node_apps/console/hooks/useNodeControl';
import { OSIcon3D } from '../OSIcon3D';
import { useAccess } from '../access/AccessProvider';
import { useAssistantIdentity } from '../../shared/identity/IdentityContext';
import { reportError } from '../../shared/errors/errorBus';
import { Minus, Maximize2, Minimize2, X, Pin, MoreHorizontal, Copy, PanelLeft, PanelRight, RefreshCw, Info, Settings } from 'lucide-react';

function NodeApp({ app, entry, revision }: { app: NonNullable<ReturnType<typeof resolveApp>>; entry: OSWindow; revision: number }) {
  const control = useNodeControl(entry.targetNodeId!);
  if (!control) return null;
  return <app.Component key={`${revision}:${entry.targetNodeId}`} nodeId={entry.targetNodeId} scope={control.scope} initialPayload={entry.initialPayload} />;
}

class WindowErrorBoundary extends React.Component<{ children: React.ReactNode; retry: string;errorLabel:string;retryLabel:string }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch(error:Error) { reportError('render_failure',error,'critical'); }
  componentDidUpdate(previous: { retry: string }) { if (previous.retry !== this.props.retry && this.state.failed) this.setState({ failed: false }); }
  render() { return this.state.failed ? <div className="os-app-state" role="alert"><p>{this.props.errorLabel}</p><button onClick={() => this.setState({ failed: false })}>{this.props.retryLabel}</button></div> : this.props.children; }
}

export function OSWindowFrame({ entry }: { entry: OSWindow }) {
  const app = resolveApp(entry.appId);
  if (!app) return null;
  return <WindowContext.Provider value={entry}><WindowRuntimeProvider><Frame entry={entry} app={app} /></WindowRuntimeProvider></WindowContext.Provider>;
}
function Frame({ entry, app }: { entry: OSWindow; app: NonNullable<ReturnType<typeof resolveApp>> }) {
  const { t, lang } = useScopedI18n('app_shell');
  const access=useAccess();
  const os=useOSApp();
  const assistant=useAssistantIdentity();
  const allowed=(app.capabilities?.length?app.capabilities:['api.admin']).every(access.can);
  const [revision, setRevision] = useState(0);
  const [menu, setMenu] = useState(false);
  const [info, setInfo] = useState(false);
  const [confirmation,setConfirmation]=useState<ToolbarItem|null>(null);
  const { snapshot, streamState } = useWindowTopology();
  const node = snapshot?.neurons.find(node => node.id === entry.targetNodeId);
  const mode = entry.windowMode || 'floating';
  const title = entry.appId === 'explorer' ? assistant.name : entry.title || getScopedString(app.scope, lang, 'title', app.name);
  const geometry = mode === 'floating' ? { left: `${entry.x}%`, top: `${entry.y}%`, width: `${entry.width}%`, height: `${entry.height}%` }
    : { left: mode.endsWith('right') || mode.endsWith('tr') || mode.endsWith('br') ? '50%' : '0', top: mode.endsWith('bl') || mode.endsWith('br') ? '50%' : '0', width: mode === 'maximized' ? '100%' : '50%', height: mode.startsWith('quarter') ? '50%' : '100%' };
  function gesture(event: React.PointerEvent, edge?: string) {
    if (event.button !== 0 || (!edge && (event.target as HTMLElement).closest('button,input,select'))) return;
    const host = event.currentTarget.closest('.os-window')?.parentElement;
    if (!host) return;
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    const bounds = host.getBoundingClientRect();
    const start = { x: event.clientX, y: event.clientY };
    let latest = { x: entry.x, y: entry.y, width: entry.width, height: entry.height };
    const target = event.currentTarget;
    const move = (e: PointerEvent) => {
      const dx = (e.clientX - start.x) / bounds.width * 100;
      const dy = (e.clientY - start.y) / bounds.height * 100;
      if (edge) {
        const right = entry.x + entry.width, bottom = entry.y + entry.height;
        const rem = parseFloat(getComputedStyle(document.documentElement).fontSize);
        const minWidth = Math.min(100, (app.window?.minWidth || (app.window?.units==='px'?480:25)) * (app.window?.units==='px'?1:rem) / bounds.width * 100);
        const minHeight = Math.min(100, (app.window?.minHeight || (app.window?.units==='px'?360:16)) * (app.window?.units==='px'?1:rem) / bounds.height * 100);
        const x = edge.includes('w') ? Math.max(0, Math.min(right - minWidth, entry.x + dx)) : entry.x;
        const y = edge.includes('n') ? Math.max(0, Math.min(bottom - minHeight, entry.y + dy)) : entry.y;
        latest = { x, y, width: edge.includes('w') ? right-x : edge.includes('e') ? Math.max(minWidth, Math.min(100-x, entry.width+dx)) : entry.width,
          height: edge.includes('n') ? bottom-y : edge.includes('s') ? Math.max(minHeight, Math.min(100-y, entry.height+dy)) : entry.height };
      } else latest = { ...latest, x: Math.max(0, Math.min(100-entry.width, entry.x+dx)), y: Math.max(0, Math.min(100-entry.height, entry.y+dy)) };
      windowStore.update(entry.id, { ...latest, windowMode: 'floating' });
    };
    const end = (e: PointerEvent) => {
      target.removeEventListener('pointermove', move);
      target.removeEventListener('pointerup', end);
      target.removeEventListener('pointercancel', cancel);
      if (!edge) {
        const x = (e.clientX-bounds.left)/bounds.width, y = (e.clientY-bounds.top)/bounds.height;
        let snap: WindowMode | undefined;
        if (x < .025 || x > .975) snap = y < .25 ? (x < .5 ? 'quarter-tl' : 'quarter-tr') : y > .75 ? (x < .5 ? 'quarter-bl' : 'quarter-br') : x < .5 ? 'snapped-left' : 'snapped-right';
        else if (y < .025) snap = 'maximized';
        if (snap) windowStore.update(entry.id, { windowMode: snap });
      }
    };
    const cancel = () => { target.removeEventListener('pointermove', move); target.removeEventListener('pointerup', end); target.removeEventListener('pointercancel', cancel); };
    target.addEventListener('pointermove', move);
    target.addEventListener('pointerup', end);
    target.addEventListener('pointercancel', cancel);
  }
  function action(id: string, value?: string) {
    if(id==='search')os.setSearchQuery(value || '');
    if (id === 'refresh'&&!app.ui) setRevision(v => v+1);
    window.dispatchEvent(new CustomEvent('nuxiva:toolbar', { detail: { windowId: entry.id, id, value } }));
  }
  const appText=(key:string)=>getScopedString(app.scope,lang,key,t(key));
  function activate(item:ToolbarItem) {
    if(!allowed||item.permissions?.some(permission=>!access.can(permission)))return;
    if(item.confirmKey)setConfirmation(item);else action(item.id);
  }
  return <section role="region" tabIndex={-1} aria-label={title} className="os-window" style={{ ...geometry, display: entry.minimized ? 'none' : undefined, zIndex: entry.z + (entry.pinned ? 100000 : 0) }} onPointerDown={() => windowStore.focus(entry.id)} onKeyDown={event => {
    if (event.key === 'Escape') { setMenu(false); setInfo(false); }
    const shortcut = app.toolbars?.flatMap(bar => bar.items).find(item => item.shortcut === event.key);
    if (shortcut) { event.preventDefault(); activate(shortcut); }
  }}>
    <header className="os-titlebar" onPointerDown={e => gesture(e)} onDoubleClick={() => app.window?.maximizable!==false&&windowStore.update(entry.id, { windowMode: mode === 'maximized' ? 'floating' : 'maximized' })}>
      <div className="os-titlebar-leading">
        <OSIcon3D name={app.name} source={app.iconUrl} size="sm" />
        {os.breadcrumbs && os.breadcrumbs.length > 0 ? (
          <nav className="os-titlebar-breadcrumbs" aria-label={t('os_path') || 'Percorso'}>
            {os.breadcrumbs.map((crumb, idx) => (
              <span key={crumb.id} className="os-breadcrumb-item">
                {idx > 0 && <span className="os-breadcrumb-sep">›</span>}
                {crumb.onClick ? (
                  <button type="button" className="os-breadcrumb-btn" onClick={crumb.onClick}>
                    {crumb.label}
                  </button>
                ) : (
                  <strong className="os-breadcrumb-current">{crumb.label}</strong>
                )}
              </span>
            ))}
          </nav>
        ) : (
          <strong className="os-titlebar-title">{title}</strong>
        )}
      </div>
      <div className="os-titlebar-actions">
        {app.target === 'node' && <select aria-label={t('os_select_node')} value={entry.targetNodeId || ''} onChange={e => windowStore.update(entry.id, { targetNodeId: e.target.value || undefined })}>
          <option value="">{t('os_select_node')}</option>
          {entry.targetNodeId && !snapshot?.neurons.some(n => n.id === entry.targetNodeId) && <option value={entry.targetNodeId}>{entry.targetNodeId}</option>}
          {snapshot?.neurons.map(n => <option key={n.id} value={n.id}>{n.name}</option>)}
        </select>}
        {os.setInspectorOpen && (
          <button
            type="button"
            className={`os-titlebar-btn os-inspector-toggle ${os.inspectorOpen ? 'os-inspector-active' : ''}`}
            aria-label={t('os_inspector') || 'Dettagli'}
            title={t('os_inspector') || 'Dettagli e anteprima'}
            onClick={() => os.setInspectorOpen?.((v) => !v)}
          >
            <PanelRight />
          </button>
        )}
        {entry.pinned && <Pin className="os-pin-indicator" aria-label={t('os_pin')} />}
        <button className="os-titlebar-btn" aria-label={t('os_window_options')} title={t('os_window_options')} aria-expanded={menu} onClick={() => setMenu(v=>!v)}><MoreHorizontal /></button>
        <button className="os-titlebar-btn" aria-label={t('os_minimize')} title={t('os_minimize')} onClick={() => windowStore.update(entry.id, { minimized: true })}><Minus /></button>
        {app.window?.maximizable!==false&&<button className="os-titlebar-btn" aria-label={t('os_maximize')} title={t('os_maximize')} onClick={() => windowStore.update(entry.id, { windowMode: mode === 'maximized' ? 'floating' : 'maximized' })}>{mode === 'maximized' ? <Minimize2 /> : <Maximize2 />}</button>}
        <button className="os-titlebar-btn os-window-close" aria-label={t('os_close')} title={t('os_close')} onClick={() => windowStore.close(entry.id)}><X /></button>
      </div>
    </header>
    {menu && <div className="os-window-menu" role="menu">
      <button role="menuitem" disabled={app.window?.singleton===true} onClick={() => { windowStore.openWindow({appId:entry.appId,targetNodeId:entry.targetNodeId,instanceKey:`instance-${Date.now()}`}); setMenu(false); }}><Copy />{t('os_new_window')}</button>
      <button role="menuitem" onClick={() => { windowStore.update(entry.id,{windowMode:'snapped-left'});setMenu(false); }}><PanelLeft />{t('os_snap_left')}</button>
      <button role="menuitem" onClick={() => { windowStore.update(entry.id,{windowMode:'snapped-right'});setMenu(false); }}><PanelRight />{t('os_snap_right')}</button>
      <button role="menuitem" aria-pressed={entry.pinned} onClick={() => { windowStore.update(entry.id,{pinned:!entry.pinned});setMenu(false); }}><Pin />{t('os_pin')}</button>
      <button role="menuitem" onClick={() => { action('refresh');setMenu(false); }}><RefreshCw />{t('os_refresh')}</button>
      {entry.appId!=='feature_settings'&&app.featureIds?.map(id=><button key={id} role="menuitem" onClick={() => { windowStore.openWindow({appId:'feature_settings',instanceKey:id});setMenu(false); }}><Settings />{app.featureIds!.length>1?`${t('os_app_settings')} · ${id}`:t('os_app_settings')}</button>)}
      <button role="menuitem" onClick={() => { setInfo(v=>!v);setMenu(false); }}><Info />{t('os_about_app')}</button>
    </div>}
    {info && <div className="os-app-info"><OSIcon3D name={app.name} source={app.iconUrl} /><strong>{title}</strong><span>{app.version || '1.0'} · {t(`os_category_${app.category || 'system'}`)}</span><button onClick={()=>setInfo(false)}>{t('os_close')}</button><a href="https://icons8.it/icons/set/person--technique-3d" target="_blank" rel="noreferrer">Icons8</a></div>}
    {app.toolbars?.map(bar => <div className="os-toolbar" key={bar.id}>{bar.items.map(item => {
      const key = item.labelKey || item.placeholderKey || item.id;
      const label = getScopedString(app.scope, lang, key, t(key));
      return item.type === 'search' ? <input key={item.id} aria-label={label} placeholder={label} value={os.searchQuery} maxLength={200} onChange={e => action(item.id, e.target.value)} />
        : item.type === 'segmented' ? <select key={item.id} aria-label={label} onChange={e => action(item.id, e.target.value)}>{item.options?.map(o => <option key={o} value={o}>{getScopedString(app.scope, lang, o)}</option>)}</select>
        : <button key={item.id} data-variant={item.variant} disabled={!allowed||item.permissions?.some(permission=>!access.can(permission))} onClick={() => activate(item)}>{item.icon&&<ManifestIcon name={item.icon}/>}<span>{label}</span></button>;
    })}</div>)}
    {confirmation&&<ActionConfirmation title={appText(confirmation.labelKey||confirmation.id)} body={appText(confirmation.confirmKey!)} cancelLabel={t('os_cancel')} confirmLabel={appText(confirmation.labelKey||confirmation.id)} danger={confirmation.variant==='danger'} onCancel={()=>setConfirmation(null)} onConfirm={()=>{if(allowed&&!confirmation.permissions?.some(permission=>!access.can(permission)))action(confirmation.id);setConfirmation(null);}}/>}
    <div className="os-content"><WindowErrorBoundary retry={`${revision}:${entry.targetNodeId}`} errorLabel={t('os_app_failed')} retryLabel={t('os_refresh')}><Suspense fallback={<p>{t('os_loading')}</p>}>
      {!access.ready?<p role="status">{t('os_loading')}</p>:!allowed?<p role="alert">{t(access.failed?'os_access_unavailable':'os_permission_denied')}</p>:app.target === 'node' ? entry.targetNodeId ? <NodeApp app={app} entry={entry} revision={revision} /> : <p>{t('os_select_node')}</p>
        : <app.Component key={revision} initialPayload={entry.initialPayload} />}
    </Suspense></WindowErrorBoundary></div>
    <footer><span className="os-connection-dot" data-live={os.status.connected ?? (node ? node.online !== false : streamState === 'live')} /><span>{node?.name || (app.target === 'node' ? t('os_select_node') : t('os_global'))}</span>{os.status.details ? <span> · {os.status.details}</span> : (app.ui?.statusBar?.showItemCount&&os.status.itemCount!==undefined&&<span> · {os.status.itemCount}</span>)}<span className="os-footer-spacer" />{node?.telemetry.pingMs != null && <span>{node.telemetry.pingMs} ms · </span>}{t('os_permissions')}</footer>
    {mode === 'floating' && app.window?.resizable !== false && ['n','ne','e','se','s','sw','w','nw'].map(edge => <div key={edge} className={`os-resize os-resize-${edge}`} onPointerDown={e => gesture(e, edge)} />)}
  </section>;
}
