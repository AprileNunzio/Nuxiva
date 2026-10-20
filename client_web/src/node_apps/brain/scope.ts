import { Box, Brain, Code2, GraduationCap, Home, LucideIcon, Search, Zap } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';

export function useBrainI18n() {
  return useScopedI18n('node_apps/brain');
}

const ROLE_ICONS: Readonly<Record<string, LucideIcon>> = {
  chat: Zap,
  deep: Brain,
  ricercatore: Search,
  domotico: Home,
  studio: GraduationCap,
  coder: Code2,
  modello3d: Box,
};

export const roleIcon = (id: string): LucideIcon => ROLE_ICONS[id] ?? Brain;

export const ORIGIN_TONE: Readonly<Record<string, string>> = {
  local: 'border-emerald-400/40 text-emerald-200',
  server: 'border-indigo-400/40 text-indigo-200',
  lan: 'border-indigo-400/40 text-indigo-200',
  cloud: 'border-amber-400/40 text-amber-200',
};

export function bytes(size: number): string {
  return size >= 1e9 ? `${(size / 1e9).toFixed(1)} GB` : `${Math.max(1, Math.round(size / 1e6))} MB`;
}

export const fieldClass =
  'rounded-xl border border-slate-700 bg-slate-950/70 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-cyan-400/70 focus-visible:ring-2 focus-visible:ring-cyan-400/40';

export const chipButton =
  'flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-semibold transition disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400';
