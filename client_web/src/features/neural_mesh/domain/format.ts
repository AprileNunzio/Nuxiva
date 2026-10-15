const formatters = new Map<string, Intl.NumberFormat>();

function formatter(locale: string, digits: number): Intl.NumberFormat {
  const key = `${locale}:${digits}`;
  const cached = formatters.get(key);
  if (cached) {
    return cached;
  }
  const created = new Intl.NumberFormat(locale, { maximumFractionDigits: digits, minimumFractionDigits: 0 });
  formatters.set(key, created);
  return created;
}

export function formatNumber(value: number | null, locale: string, digits = 1): string | null {
  return value === null ? null : formatter(locale, digits).format(value);
}

export function formatPercent(value: number | null, locale: string): string | null {
  return value === null ? null : `${formatter(locale, 0).format(value)}%`;
}

export function formatPair(used: number | null, total: number | null, locale: string, unit: string): string | null {
  if (used === null && total === null) {
    return null;
  }
  const left = formatNumber(used ?? 0, locale);
  const right = formatNumber(total, locale);
  return right === null ? `${left} ${unit}` : `${left} / ${right} ${unit}`;
}

export function formatRate(kbps: number | null, locale: string): string | null {
  if (kbps === null) {
    return null;
  }
  return kbps >= 1024 ? `${formatNumber(kbps / 1024, locale)} Mb/s` : `${formatNumber(kbps, locale, 0)} kb/s`;
}
