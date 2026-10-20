import React from 'react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { ApplicationLayout } from '../../app_shell/window_manager/ApplicationLayout';
import { ApplicationCatalog } from '../../app_shell/window_manager/ApplicationCatalog';
import { appRegistry } from '../../app_shell/window_manager/registry';
import { useOSApp } from '../../app_shell/window_manager/WindowContext';
import { useResource } from '../shared/useResource';
import { FeaturesOverview } from '../shared/featureTypes';
import { overviewUrl } from './api';
import { isApplication } from '../../app_shell/window_manager/app_scanner';
export function View() {
 const {openApp}=useOSApp();
 const {t,lang}=useScopedI18n('core_apps/features_hub');
 const {data,error,loading,reload}=useResource<FeaturesOverview>(overviewUrl(lang),15000);
 const findApp=(id:string)=>appRegistry.find(app=>(app.id===id||app.featureIds?.includes(id))&&app.target!=='node');
 const isExcludedFromHub = (id: string) => isApplication({ id }) || id === 'applications';
 if(!data)return <ApplicationLayout sections={{}} loading={loading} error={error?t('unreachable'):undefined} onRetry={reload}/>;
 return <ApplicationCatalog lang={lang} labels={{search:t('search'),clearSearch:t('clear_search'),categories:t('navigation'),all:t('all_categories'),empty:t('empty'),emptyHint:t('empty_hint'),stateFilter:t('state_filter'),allStates:t('all_states'),on:t('running'),off:t('stopped'),reset:t('reset_filters'),pinToDesktop:t('pin_to_desktop'),unpinFromDesktop:t('unpin_from_desktop'),open:t('open_app')}} categories={Object.fromEntries(Object.entries(data.categories).map(([id,label])=>[id,t(`category_${id}`)===`category_${id}`?label:t(`category_${id}`)]))} items={data.features.filter(f => !isExcludedFromHub(f.id)).map(feature=>({id:feature.id,label:feature.name,description:feature.description,category:feature.category,active:feature.state.enabled,icon:feature.icon_url||findApp(feature.id)?.iconUrl,symbol:feature.icon}))} onOpen={id=>openApp(findApp(id)?{appId:findApp(id)!.id}:{appId:'feature_settings',instanceKey:id})}/>;
}
export default View;
