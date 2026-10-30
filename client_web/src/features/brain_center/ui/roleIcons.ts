import { Box, Code2, GraduationCap, Home, LucideIcon, MessageCircle, Search, Workflow } from 'lucide-react';

const ROLE_ICONS: Readonly<Record<string, LucideIcon>> = {
  chat: MessageCircle,
  deep: Workflow,
  ricercatore: Search,
  domotico: Home,
  studio: GraduationCap,
  coder: Code2,
  modello3d: Box,
};

export const roleIcon = (id: string): LucideIcon => ROLE_ICONS[id] ?? Workflow;

export const PRIMARY_ROLES: readonly string[] = ['chat', 'deep'];
