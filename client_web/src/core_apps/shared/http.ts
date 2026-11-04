import { requestJson } from '../../node_apps/shared/data/http';

export type Json = Record<string, unknown>;

export const getJson = <T = Json>(url: string, signal?: AbortSignal) => requestJson<T>(url, { signal });

export const sendJson = <T = Json>(url: string, method: 'POST' | 'PUT' | 'PATCH' | 'DELETE', body?: unknown) =>
  requestJson<T>(url, { method, body: body === undefined ? undefined : JSON.stringify(body) });

export const asList = <T = Json>(value: unknown): T[] => (Array.isArray(value) ? (value as T[]) : []);

export const asObject = (value: unknown): Json =>
  typeof value === 'object' && value !== null && !Array.isArray(value) ? (value as Json) : {};

export const text = (value: unknown, fallback = ''): string => (typeof value === 'string' ? value : fallback);

export const num = (value: unknown, fallback = 0): number => (typeof value === 'number' && Number.isFinite(value) ? value : fallback);

export const flag = (value: unknown): boolean => value === true;
