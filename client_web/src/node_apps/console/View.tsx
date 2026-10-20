import React from 'react';
import { NodeConsoleView } from './NodeConsoleView';
import { appRegistry } from '../../app_shell/window_manager/registry';
import { OSIcon3D } from '../../app_shell/OSIcon3D';
import { getScopedString, useScopedI18n } from '../../shared/i18n/useScopedI18n';
import './desktop.css';
export const View: React.FC<{ nodeId?: string; initialPayload?: Record<string, unknown> }> = ({ nodeId = '', initialPayload }) => {
  const { lang, t } = useScopedI18n('node_apps/console');
  return <div><NodeConsoleView standaloneApps nodeId={nodeId} initialName={typeof initialPayload?.name === 'string' ? initialPayload.name : nodeId}
    onBack={() => window.NuxivaOS.openWindow({ appId: 'mesh' })} onRenamed={() => {}} />
    <section className="node-os-apps"><h2>{t('modules_label')}</h2><div>{appRegistry.filter(app => (app.target === 'node' || app.target === 'universal') && app.id !== 'node_apps/console').map(app => <button key={app.id} onClick={() => window.NuxivaOS.openWindow({appId:app.id,targetNodeId:nodeId})}><OSIcon3D name={app.name} source={app.iconUrl} /><span>{getScopedString(app.scope,lang,'title',app.name)}</span></button>)}</div></section>
  </div>;
};
