export function compactNumber(value: number, locale: string): string {
  return new Intl.NumberFormat(locale, { notation: 'compact', maximumFractionDigits: 1 }).format(Math.max(0, value));
}

export function bytes(size: number): string {
  return size >= 1e9 ? `${(size / 1e9).toFixed(1)} GB` : `${Math.max(1, Math.round(size / 1e6))} MB`;
}

export function share(used: number, cap: number | null): number | null {
  return cap && cap > 0 ? Math.min(1, Math.max(0, used / cap)) : null;
}

export function parseAmount(raw: string): number | null | undefined {
  const clean = raw.replace(/[\s.,_']/g, '');
  if (clean === '') {
    return null;
  }
  if (!/^\d{1,13}$/.test(clean)) {
    return undefined;
  }
  const value = Number(clean);
  return value > 0 && value <= 1_000_000_000_000 ? value : undefined;
}

export function matches(query: string, ...fields: readonly string[]): boolean {
  const needle = query.trim().toLocaleLowerCase();
  return needle === '' || fields.some((field) => field.toLocaleLowerCase().includes(needle));
}
