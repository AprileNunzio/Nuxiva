import React, { Component, ErrorInfo, ReactNode } from 'react';
import { i18n } from '../i18n/i18nService';
import { globalErrorHandler } from './globalErrorHandler';
import { SystemRuntimeError } from './errorTypes';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  errorMessage: string;
}

export class ErrorBoundary extends Component<Props, State> {
  public override state: State = {
    hasError: false,
    errorMessage: ''
  };

  public static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      errorMessage: error.message || 'System fault'
    };
  }

  public override componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    globalErrorHandler.dispatch(
      new SystemRuntimeError(`${error.message} - ${errorInfo.componentStack}`)
    );
  }

  private handleReload = (): void => {
    window.location.reload();
  };

  public override render(): ReactNode {
    if (this.state.hasError) {
      const dict = i18n.getDictionary();
      return (
        <div style={{
          position: 'fixed',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#070a12',
          color: '#f0ece1',
          zIndex: 9999,
          padding: '24px',
          textAlign: 'center'
        }}>
          <h1 style={{ color: '#d4af37', marginBottom: '12px', fontSize: '1.5rem' }}>
            {dict.dialog.errorTitle}
          </h1>
          <p style={{ color: '#9aa0a6', maxWidth: '420px', marginBottom: '24px', fontSize: '0.9rem' }}>
            {dict.dialog.errorSubtitle}
          </p>
          <button
            onClick={this.handleReload}
            style={{
              padding: '10px 20px',
              borderRadius: '999px',
              border: '1px solid #d4af37',
              background: 'rgba(212, 175, 55, 0.2)',
              color: '#f5d76e',
              cursor: 'pointer',
              fontWeight: 600
            }}
          >
            {dict.dialog.retry}
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
