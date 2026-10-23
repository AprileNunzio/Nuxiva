import React, { Suspense, lazy } from 'react';
import { AppShell } from './app_shell/AppShell';
import { AuthGate } from './features/auth_gate';
import { ErrorToastHost } from './shared/errors/ErrorToastHost';
import { GlobalErrorBoundary } from './shared/errors/GlobalErrorBoundary';
import { I18nProvider } from './shared/i18n/I18nContext';
import { UpdateBanner } from './shared/updates/UpdateBanner';
import { IdentityProvider } from './shared/identity/IdentityContext';
const Workbench = lazy(() => import('./apps/repair_workbench/View'));

function ApplicationSurface() {
  if (window.location.pathname === '/repair-workbench') {
    const query = new URLSearchParams(window.location.search);
    return <Suspense fallback={null}><Workbench initialPayload={{
      projectId: query.get('project') || undefined,
      sessionId: query.get('session') || undefined,
      takeover: true,
    }} /></Suspense>;
  }
  return <AuthGate><AppShell /></AuthGate>;
}

export const App: React.FC = () => (
  <I18nProvider>
    <IdentityProvider>
      <GlobalErrorBoundary>
        <ApplicationSurface />
      </GlobalErrorBoundary>
      <ErrorToastHost />
      <UpdateBanner />
    </IdentityProvider>
  </I18nProvider>
);

export default App;
