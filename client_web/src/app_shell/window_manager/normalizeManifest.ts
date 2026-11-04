import type { AppManifest, UIRequirements } from './types';
export function normalizeManifest(raw: unknown, scope:string):AppManifest | null {
  if(!raw || typeof raw!=='object')return null;
  const input=raw as AppManifest;
  if(typeof input.id!=='string'||!/^[-a-zA-Z0-9_]+$/.test(input.id))return null;
  if(input.window!==undefined&&(!input.window||typeof input.window!=='object'||Array.isArray(input.window)))return null;
  for(const value of [input.window?.defaultWidth,input.window?.defaultHeight,input.window?.minWidth,input.window?.minHeight])if(value!==undefined&&(!Number.isFinite(value)||value<=0))return null;
  if(input.capabilities!==undefined&&(!Array.isArray(input.capabilities)||input.capabilities.some(value=>typeof value!=='string'||!value)))return null;
  const ui=input.ui as UIRequirements | undefined;
  const modern=ui!==undefined;
  if(modern) {
    if(!ui||typeof ui!=='object'||Array.isArray(ui))return null;
    for(const items of [ui.tabs,ui.actions])if(items!==undefined&&(!Array.isArray(items)||items.some(item=>!item||typeof item.id!=='string'||typeof item.labelKey!=='string')))return null;
    if(ui.actions?.some(item=>item.permissions!==undefined&&(!Array.isArray(item.permissions)||item.permissions.some(permission=>typeof permission!=='string'))))return null;
  }
  const window={...input.window,units:modern?'px' as const:'legacy' as const};
  const toolbars=modern?[{id:'declared',items:[
    ...(ui.searchable?[{id:'search',type:'search' as const,placeholderKey:ui.searchPlaceholderKey || 'os_search'}]:[]),
    ...(ui.actions || []).map(item=>({...item,type:'action' as const})),
  ]}]:input.toolbars;
  return {...input,name:input.name || input.id,scope,i18nScope:input.i18nScope || scope,
    window,toolbars,navigation:ui?.tabs || input.navigation};
}
