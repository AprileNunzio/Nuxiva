import React, { useEffect } from 'react';
import { ApplicationLayout } from '../../app_shell/window_manager/ApplicationLayout';
import { useOSApp } from '../../app_shell/window_manager/WindowContext';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { useResource, useAction } from '../shared/useResource';
import { FeaturesOverview } from '../shared/featureTypes';
import { setMode } from '../shared/featureApi';
import { SettingsEditor } from '../shared/SettingsEditor';
export function View() {
 const os=useOSApp(),{t,lang}=useScopedI18n('core_apps/feature_settings');
 const {data,loading,error,reload}=useResource<FeaturesOverview>(`/api/features?lang=${encodeURIComponent(lang)}`,15000);
 const {busy,run}=useAction(reload),feature=data?.features.find(item=>item.id===os.instanceKey);
 useEffect(()=>{if(feature)os.setTitle(feature.name);},[os.windowId,feature?.name]);
 if(!feature)return <ApplicationLayout sections={{}} loading={loading} error={t(error?'unreachable':'empty')} onRetry={reload}/>;
 return <ApplicationLayout sections={{settings:<div><h1>{feature.name}</h1><p className="mb-5 text-sm text-slate-500">{feature.description}</p><label className="mb-5 flex flex-wrap items-center gap-3">{t('mode')}<select disabled={busy} value={feature.state.mode} onChange={event=>void run(()=>setMode(feature.id,event.target.value),'features_mode_failed')}><option value="auto">{t('mode_auto')}</option><option value="1">{t('mode_on')}</option><option value="0">{t('mode_off')}</option></select><span role="status">{t(feature.state.enabled?'running':'stopped')}</span></label><SettingsEditor key={feature.id} feature={feature} busy={busy} t={t} run={run}/></div>,details:<div><h1>{feature.name}</h1><p>{feature.description}</p><ul className="mt-4 space-y-2">{feature.capabilities.map(capability=><li key={capability}>{capability}</li>)}</ul><p className="mt-4 text-sm text-slate-500">{feature.state.reason}</p></div>}}/>;
}
