export abstract class AppBaseError extends Error {
  public abstract readonly code: string;
  public readonly timestamp: number;

  constructor(message: string) {
    super(message);
    this.name = this.constructor.name;
    this.timestamp = Date.now();
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

export class GameLogicError extends AppBaseError {
  public readonly code = 'ERR_GAME_LOGIC';
}

export class ResourceLoadError extends AppBaseError {
  public readonly code = 'ERR_RESOURCE_LOAD';
  constructor(message: string, public readonly resourceUri?: string) {
    super(message);
  }
}

export class SecurityError extends AppBaseError {
  public readonly code = 'ERR_SECURITY_VIOLATION';
}

export class SystemRuntimeError extends AppBaseError {
  public readonly code = 'ERR_SYSTEM_RUNTIME';
}
