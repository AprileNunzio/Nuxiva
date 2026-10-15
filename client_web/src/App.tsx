import React from 'react';
import { AppShell } from './app_shell/AppShell';
import { ErrorToastHost } from './shared/errors/ErrorToastHost';
import { GlobalErrorBoundary } from './shared/errors/GlobalErrorBoundary';
import { I18nProvider } from './shared/i18n/I18nContext';

export const App: React.FC = () => (
  <I18nProvider>
    <GlobalErrorBoundary>
      <AppShell />
    </GlobalErrorBoundary>
    <ErrorToastHost />
  </I18nProvider>
);

export default App;
