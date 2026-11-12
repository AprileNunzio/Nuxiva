const CONTROL_CHARS = /[\u0000-\u001F\u007F-\u009F​-‏‪-‮⁦-⁩﻿]/g;
const ID_PATTERN = /^[A-Za-z0-9._:@-]{1,128}$/;
const IPV4_PATTERN = /^(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}$/;
const IPV6_PATTERN = /^[0-9A-Fa-f:.]{2,45}$/;

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function cleanText(value: unknown, maxLength: number): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  const normalized = value.normalize('NFKC').replace(CONTROL_CHARS, '').trim();
  return normalized.length === 0 ? null : normalized.slice(0, maxLength);
}

export function cleanId(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  const trimmed = value.trim();
  return ID_PATTERN.test(trimmed) ? trimmed : null;
}

export function cleanIp(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  const trimmed = value.trim();
  if (IPV4_PATTERN.test(trimmed)) {
    return trimmed === '0.0.0.0' ? null : trimmed;
  }
  return trimmed.includes(':') && IPV6_PATTERN.test(trimmed) ? trimmed : null;
}

export function cleanNumber(value: unknown, min: number, max: number): number | null {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return null;
  }
  return Math.min(max, Math.max(min, value));
}

export function cleanBoolean(value: unknown): boolean {
  return value === true;
}
