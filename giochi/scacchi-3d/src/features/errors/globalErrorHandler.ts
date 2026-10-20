import { AppBaseError, SystemRuntimeError } from './errorTypes';

type ErrorObserver = (error: AppBaseError) => void;

class GlobalErrorHandler {
  private static instance: GlobalErrorHandler;
  private observers: Set<ErrorObserver> = new Set();
  private isInitialized = false;

  private constructor() {}

  public static getInstance(): GlobalErrorHandler {
    if (!GlobalErrorHandler.instance) {
      GlobalErrorHandler.instance = new GlobalErrorHandler();
    }
    return GlobalErrorHandler.instance;
  }

  public init(): void {
    if (this.isInitialized || typeof window === 'undefined') return;
    this.isInitialized = true;

    window.addEventListener('error', (event) => {
      const err = event.error instanceof AppBaseError 
        ? event.error 
        : new SystemRuntimeError(event.message || 'Unknown runtime error');
      this.dispatch(err);
    });

    window.addEventListener('unhandledrejection', (event) => {
      const reason = event.reason;
      const err = reason instanceof AppBaseError 
        ? reason 
        : new SystemRuntimeError(typeof reason === 'string' ? reason : reason?.message || 'Unhandled Promise Rejection');
      this.dispatch(err);
    });
  }

  public subscribe(observer: ErrorObserver): () => void {
    this.observers.add(observer);
    return () => {
      this.observers.delete(observer);
    };
  }

  public dispatch(error: AppBaseError): void {
    console.error(`[${error.code}] ${error.message}`);
    for (const observer of this.observers) {
      observer(error);
    }
  }
}

export const globalErrorHandler = GlobalErrorHandler.getInstance();
