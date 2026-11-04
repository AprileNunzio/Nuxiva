import React, { createContext, useContext, useEffect, useState } from 'react';
import type { OSWindow, OSAppContextValue } from './types';
import { windowStore } from './WindowStore';
export const WindowContext = createContext<OSWindow | null>(null);
const RuntimeContext=createContext<Pick<OSAppContextValue,'searchQuery'|'setSearchQuery'|'status'|'setStatus'|'breadcrumbs'|'setBreadcrumbs'|'inspectorOpen'|'setInspectorOpen'|'selectedId'|'setSelectedId'>|null>(null);
export function WindowRuntimeProvider({children}:{children:React.ReactNode}) {
  const [searchQuery,setQuery]=useState('');
  const [status,setStatus]=useState<{itemCount?:number;connected?:boolean;details?:string}>({});
  const [breadcrumbs,setBreadcrumbs]=useState<readonly import('./types').BreadcrumbItem[]>([]);
  const [inspectorOpen,setInspectorOpen]=useState(true);
  const [selectedId,setSelectedId]=useState<string|undefined>(undefined);
  return <RuntimeContext.Provider value={{
    searchQuery,
    setSearchQuery:query=>setQuery(query.replace(/[\u0000-\u001f\u007f]/g,'').slice(0,200)),
    status,
    setStatus,
    breadcrumbs,
    setBreadcrumbs,
    inspectorOpen,
    setInspectorOpen,
    selectedId,
    setSelectedId
  }}>{children}</RuntimeContext.Provider>;
}
export function useOSApp():OSAppContextValue {
  const entry=useContext(WindowContext),runtime=useContext(RuntimeContext);
  if(!entry||!runtime)throw new Error('Missing OS application context');
  return {...runtime,windowId:entry.id,appId:entry.appId,nodeId:entry.targetNodeId,instanceKey:entry.instanceKey,activeTab:entry.activeSection,
    setActiveTab:id=>windowStore.update(entry.id,{activeSection:id}),setNodeId:id=>windowStore.update(entry.id,{targetNodeId:id}),
    setTitle:title=>windowStore.update(entry.id,{title:title.slice(0,200)}),openApp:request=>windowStore.openWindow(request)};
}
export function useWindowNodeContext() {
  const window = useContext(WindowContext);
  return { nodeId: window?.targetNodeId, payload: window?.initialPayload, windowId: window?.id };
}
export function useWindowToolbar(handler: (id: string, value?: string) => void) {
  const context = useContext(WindowContext);
  useEffect(() => {
    const listener = (event: Event) => {
      const detail = (event as CustomEvent).detail;
      if (detail.windowId === context?.id) handler(detail.id, detail.value);
    };
    window.addEventListener('nuxiva:toolbar', listener);
    return () => window.removeEventListener('nuxiva:toolbar', listener);
  }, [context?.id, handler]);
}
