import { NeuronKind } from './types';

export const CORE_COLOR = '#7dd3fc';

export const KIND_COLORS: Readonly<Record<NeuronKind, string>> = {
  compute: '#22d3ee',
  satellite: '#34d399',
  micro: '#fbbf24',
  mobile: '#a78bfa',
};

export const STALE_COLOR = '#f59e0b';

export function withAlpha(hex: string, alpha: number): string {
  const value = hex.replace('#', '');
  const r = parseInt(value.slice(0, 2), 16);
  const g = parseInt(value.slice(2, 4), 16);
  const b = parseInt(value.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${Math.min(1, Math.max(0, alpha))})`;
}
