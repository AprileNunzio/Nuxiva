import React from 'react';
import { AppShell } from './app_shell/AppShell';
import { AuthGate } from './features/auth_gate';
import { ErrorToastHost } from './shared/errors/ErrorToastHost';
import { GlobalErrorBoundary } from './shared/errors/GlobalErrorBoundary';
import { I18nProvider } from './shared/i18n/I18nContext';
import { IdentityProvider } from './shared/identity/IdentityContext';

export const App: React.FC = () => (
  <I18nProvider>
    <IdentityProvider>
      <GlobalErrorBoundary>
        <AuthGate>
          <AppShell />
        </AuthGate>
      </GlobalErrorBoundary>
      <ErrorToastHost />
    </IdentityProvider>
  </I18nProvider>
);

export default App;
