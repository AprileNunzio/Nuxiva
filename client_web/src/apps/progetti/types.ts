export const STATUSES = ['planning', 'running', 'waiting_user', 'paused', 'completed', 'failed', 'cancelled'] as const;
export type ProjectStatus = (typeof STATUSES)[number];

export interface ProjectInfo {
  readonly id: string;
  readonly title: string;
  readonly goal: string;
  readonly status: ProjectStatus;
  readonly archived?: boolean;
  readonly assignees?: readonly string[];
  readonly usage?: { readonly tokens: number; readonly seconds: number };
  readonly budget?: { readonly tokens: number };
}

export interface Progress {
  readonly total: number;
  readonly done: number;
  readonly review: number;
  readonly running: number;
  readonly failed: number;
  readonly percent: number;
}

export interface ProjectSummary {
  readonly project: ProjectInfo;
  readonly progress: Progress;
}

export interface TaskInfo {
  readonly id: string;
  readonly title: string;
  readonly role: string;
  readonly status: string;
  readonly attempts: number;
}

export interface ProjectDetail extends ProjectSummary {
  readonly tasks: readonly TaskInfo[];
}

export interface Overview {
  readonly projects: readonly ProjectSummary[];
}

export type ControlAction = 'pause' | 'resume' | 'cancel';
export type ReviewAction = 'approve' | 'rework' | 'interrupt';
