import { reportError } from './errorBus';

let installed = false;

export function installGlobalErrorHandlers(): void {
  if (installed) {
    return;
  }
  installed = true;
  window.addEventListener('error', (event: ErrorEvent) => {
    reportError('unhandled_exception', event.error ?? event.message, 'critical');
  });
  window.addEventListener('unhandledrejection', (event: PromiseRejectionEvent) => {
    reportError('unhandled_rejection', event.reason, 'critical');
  });
}
