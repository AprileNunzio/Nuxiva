import React, { useEffect, useState } from 'react';
import { adminPath } from '../shared/http/basePath';
import { subscribeErrors } from '../shared/errors/errorBus';
import { getScopedString, useScopedI18n } from '../shared/i18n/useScopedI18n';
import { resolveApp } from './window_manager/registry';
import { windowStore } from './window_manager/WindowStore';
import type { OSWindowOpenRequest } from './window_manager/types';

interface Notification { id: string; key: string; scope: string; at: number; action?: OSWindowOpenRequest }
export function NotificationCenter({ visible, onClose, onCountChange }: { visible: boolean; onClose: () => void; onCountChange: (count: number) => void }) {
  const { t, lang } = useScopedI18n('app_shell');
  const [items, setItems] = useState<Notification[]>([]);
  useEffect(() => onCountChange(items.length), [items.length,onCountChange]);
  useEffect(() => {
    const append = (item: Notification) => setItems(current => current.some(n => n.id === item.id) ? current : [item, ...current].slice(0, 100));
    const unsubscribe = subscribeErrors(error => append({ id: `error:${error.id}`, key: error.code, scope: 'shared/errors', at: error.occurredAt }));
    const stream = new EventSource(`${adminPath('/api/bus/stream')}?topics=ui.notification.*,ui.window.open`, { withCredentials: true });
    stream.onmessage = event => {
      if (event.data.length > 65536) return;
      try {
        const envelope = JSON.parse(event.data);
        const payload = envelope.payload;
        if (!payload || typeof envelope.id !== 'string' || typeof envelope.topic !== 'string') return;
        const request = envelope.topic === 'ui.window.open' ? payload : payload.action;
        const action = request && typeof request.appId === 'string' && resolveApp(request.appId) ? {
          appId: request.appId,
          targetNodeId: typeof request.targetNodeId === 'string' ? request.targetNodeId : undefined,
          instanceKey: typeof request.instanceKey === 'string' ? request.instanceKey : undefined,
          initialPayload: request.initialPayload && typeof request.initialPayload === 'object' && !Array.isArray(request.initialPayload) ? request.initialPayload : undefined,
        } : undefined;
        append({ id: envelope.id, key: typeof payload.labelKey === 'string' ? payload.labelKey : 'os_system_event', scope: action ? resolveApp(action.appId)!.scope : 'app_shell', at: Number.isFinite(envelope.ts) ? envelope.ts * 1000 : Date.now(), action });
      } catch {
        return;
      }
    };
    return () => { unsubscribe(); stream.close(); };
  }, []);
  return <>{visible && <aside className="os-notifications"><header><h2>{t('os_notifications')}</h2><button aria-label={t('os_close')} onClick={onClose}>×</button></header>
      <button onClick={() => setItems([])}>{t('os_clear')}</button>
      {!items.length && <p>{t('os_no_notifications')}</p>}
      {items.map(item => <article key={item.id}><strong>{getScopedString(item.scope, lang, item.key, t(item.key))}</strong>
        <p>{new Date(item.at).toLocaleString(lang)}</p>
        {item.action && <button onClick={() => windowStore.openWindow(item.action!)}>{getScopedString(resolveApp(item.action.appId)!.scope, lang, 'title', item.action.appId)}</button>}
      </article>)}
    </aside>}
  </>;
}
