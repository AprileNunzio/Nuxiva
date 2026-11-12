import React from 'react';
import { AppViewFrame } from '../shared/kit';
import { useSentinel } from './useSentinel';
import { Timeline } from './Timeline';
import { Header } from './Header';
import { Settings } from './Settings';
import { NativeGate } from './NativeGate';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import './sentinel.css';

export function View() {
  const {t}=useScopedI18n('apps/sentinel');
  return <NativeGate t={t}><Sentinel/></NativeGate>;
}

function Sentinel() {
  const model=useSentinel(), {t,status}=model;
  if(status.data&&!status.data.enabled)return <p className="sentinel-empty" role="alert">{t('disabled')}</p>;
  return <AppViewFrame header={<Header model={model}/>} sections={{
    diary:<Timeline model={model}/>,
    people:<Timeline model={model} groups={['presence','appearance']}/>,
    guests:<Timeline model={model} groups={['guest']}/>,
    security:<Timeline model={model} groups={['access','display','voice']}/>,
    nuxiva:<Timeline model={model} groups={['automation','self','system','sentinel']}/>,
    settings:<Settings model={model}/>,
  }}/>;
}
