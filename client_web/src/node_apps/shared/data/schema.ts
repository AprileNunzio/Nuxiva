export type SettingSpec =
  | { readonly key: string; readonly kind: 'toggle'; readonly fallback: boolean }
  | {
      readonly key: string;
      readonly kind: 'range';
      readonly min: number;
      readonly max: number;
      readonly step: number;
      readonly fallback: number;
      readonly unit?: string;
    }
  | { readonly key: string; readonly kind: 'choice'; readonly options: readonly string[]; readonly fallback: string }
  | { readonly key: string; readonly kind: 'color'; readonly fallback: string };

const HEX_COLOR = /^#[0-9a-f]{6}$/;

export function readColor(raw: string, fallback: string): string {
  const value = raw.trim().toLowerCase();
  return HEX_COLOR.test(value) ? value : fallback;
}

export function readToggle(raw: string, fallback: boolean): boolean {
  const value = raw.trim().toLowerCase();
  if (!value) {
    return fallback;
  }
  return !['0', 'off', 'no', 'false'].includes(value);
}

export function readRange(raw: string, min: number, max: number, fallback: number): number {
  const parsed = Number.parseFloat(raw);
  return Number.isFinite(parsed) ? Math.min(max, Math.max(min, parsed)) : fallback;
}

export function readChoice(raw: string, options: readonly string[], fallback: string): string {
  const value = raw.trim().toLowerCase();
  return options.includes(value) ? value : fallback;
}

export function effectiveValue(spec: SettingSpec, raw: string): boolean | number | string {
  switch (spec.kind) {
    case 'toggle':
      return readToggle(raw, spec.fallback);
    case 'range':
      return readRange(raw, spec.min, spec.max, spec.fallback);
    case 'color':
      return readColor(raw, spec.fallback);
    default:
      return readChoice(raw, spec.options, spec.fallback);
  }
}

export function serialize(spec: SettingSpec, value: boolean | number | string): string {
  if (spec.kind === 'toggle') {
    return value ? '1' : '0';
  }
  if (spec.kind === 'range') {
    const decimals = spec.step < 1 ? Math.max(0, -Math.floor(Math.log10(spec.step))) : 0;
    return Number(value).toFixed(decimals);
  }
  if (spec.kind === 'color') {
    return readColor(String(value), spec.fallback);
  }
  return String(value);
}
