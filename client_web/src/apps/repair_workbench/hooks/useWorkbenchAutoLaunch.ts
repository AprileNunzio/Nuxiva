import { useEffect, useRef } from 'react';
import { windowStore } from '../../../app_shell/window_manager/WindowStore';
import { reportError } from '../../../shared/errors/errorBus';
import { fetchPendingWorkbenchLaunches } from '../api';

export function useWorkbenchAutoLaunch(enabled: boolean): void {
  const sinceRef = useRef<number>(Date.now() / 1000 - 2);
  const seenRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (!enabled) return;
    let active = true;
    const poll = async () => {
      try {
        const requests = await fetchPendingWorkbenchLaunches(sinceRef.current);
        if (!active || requests.length === 0) return;
        for (const req of requests) {
          if (seenRef.current.has(req.launch_id)) continue;
          seenRef.current.add(req.launch_id);
          sinceRef.current = Math.max(sinceRef.current, req.created_at);
          windowStore.closeAll();
          windowStore.openWindow({
            appId: 'repair_workbench',
            windowMode: 'maximized',
            initialPayload: { projectId: req.project_id, takeover: true },
          });
        }
      } catch (cause: unknown) {
        reportError('repair_workbench_autolaunch_poll', cause);
      }
    };
    const timer = window.setInterval(() => void poll(), 4000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [enabled]);
}
