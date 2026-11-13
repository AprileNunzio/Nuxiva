export type Translate = (key: string, params?: Record<string, string | number>) => string;
export type Run = <R>(task: () => Promise<R>, code?: string) => Promise<R | null>;
