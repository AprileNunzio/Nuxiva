import { useCallback, useState } from 'react';
import {
  ContextManifest,
  IDLE_CONTEXT_MANIFEST,
  NotificationEvent,
} from './contextManifest';
import { evaluateSpatialArbitration } from './spatialArbiter';

export { evaluateSpatialArbitration };

export function useSpatialArbiter() {
  const [activeContext, setActiveContextState] = useState<ContextManifest>(IDLE_CONTEXT_MANIFEST);
  const [deferredQueue, setDeferredQueue] = useState<NotificationEvent[]>([]);
  const [criticalEvent, setCriticalEvent] = useState<NotificationEvent | null>(null);
  const [activePipNotification, setActivePipNotification] = useState<NotificationEvent | null>(null);

  const setContext = useCallback((manifest: ContextManifest) => {
    setActiveContextState(manifest);
    if (manifest.focusLockLevel === 0) {
      setDeferredQueue([]);
    }
  }, []);

  const dispatchNotification = useCallback(
    (event: NotificationEvent) => {
      const res = evaluateSpatialArbitration(event, activeContext);
      if (res.action === 'PREEMPTION_TOTAL') {
        setCriticalEvent(event);
      } else if (res.action === 'SMART_PIP') {
        setActivePipNotification(event);
      } else if (res.shouldDefer) {
        setDeferredQueue((prev) => [...prev, event]);
      }
      return res;
    },
    [activeContext]
  );

  const dismissCritical = useCallback(() => {
    setCriticalEvent(null);
  }, []);

  const dismissPip = useCallback(() => {
    setActivePipNotification(null);
  }, []);

  return {
    activeContext,
    setContext,
    assistantMorphology: activeContext.assistantRequirement.preferredMorphology,
    deferredQueue,
    criticalEvent,
    activePipNotification,
    dispatchNotification,
    dismissCritical,
    dismissPip,
  };
}
