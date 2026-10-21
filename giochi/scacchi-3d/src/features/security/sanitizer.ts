export class Sanitizer {
  public static sanitizeString(input: unknown): string {
    if (typeof input !== 'string') {
      return '';
    }
    return input
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#x27;')
      .replace(/\//g, '&#x2F;');
  }

  public static sanitizeAlphaNumeric(input: unknown): string {
    if (typeof input !== 'string') {
      return '';
    }
    return input.replace(/[^a-zA-Z0-9_\-\s]/g, '').trim();
  }

  public static safeJsonParse<T>(raw: string | null, fallback: T): T {
    if (!raw || typeof raw !== 'string') {
      return fallback;
    }
    try {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === 'object') {
        Reflect.deleteProperty(parsed, '__proto__');
        Reflect.deleteProperty(parsed, 'constructor');
        Reflect.deleteProperty(parsed, 'prototype');
      }
      return parsed as T;
    } catch {
      return fallback;
    }
  }
}
