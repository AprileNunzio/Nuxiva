import { Activity, Gauge, HardDrive, KeyRound, LayoutDashboard, MessagesSquare, SlidersHorizontal, LucideIcon } from 'lucide-react';

export const SECTION_IDS = ['overview', 'contexts', 'providers', 'local_models', 'usage', 'functions', 'advanced'] as const;

export type SectionId = (typeof SECTION_IDS)[number];

export const SECTION_ICONS: Readonly<Record<SectionId, LucideIcon>> = {
  overview: LayoutDashboard,
  contexts: MessagesSquare,
  providers: KeyRound,
  local_models: HardDrive,
  usage: Gauge,
  functions: Activity,
  advanced: SlidersHorizontal,
};

export const isSection = (value: unknown): value is SectionId => SECTION_IDS.some((id) => id === value);
