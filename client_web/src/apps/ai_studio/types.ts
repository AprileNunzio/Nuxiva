export type ModelMode = 'fast' | 'reasoning' | 'creative' | 'code';

export interface Project {
  id: string;
  name: string;
  description: string;
  instructions: string;
  smb_folder: string;
  created_at: number;
  updated_at: number;
  thread_count: number;
}

export interface Thread {
  id: string;
  project_id: string | null;
  title: string;
  pinned: boolean;
  model_mode: ModelMode;
  created_at: number;
  updated_at: number;
  message_count: number;
}

export interface Attachment {
  id: string;
  name: string;
  size: number;
  mime_type: string;
  kind: string;
  path: string;
  data_url?: string;
}

export interface Artifact {
  id: string;
  identifier: string;
  title: string;
  kind: 'code' | 'html' | 'svg' | 'diagram' | 'markdown' | '3d';
  language: string;
  content: string;
}

export interface MemoryFact {
  id: string;
  source: string;
  content: string;
  speaker: string;
  timestamp: number;
  tags: string[];
}

export interface AgentAction {
  id: string;
  kind: 'wait' | 'command' | 'analyze' | 'edit' | 'task' | 'think';
  label?: string;

  target?: string;
  ext?: string;
  lines?: string;
  added?: number;
  removed?: number;
  detail?: string;
  duration?: string;
  diff_id?: string;
}

export interface DiffLine {
  type: 'add' | 'del' | 'same';
  oldNum?: number;
  newNum?: number;
  text: string;
}

export interface FileDiff {
  id: string;
  filename: string;
  ext: string;
  added: number;
  removed: number;
  before_content: string;
  after_content: string;
  lines?: DiffLine[];
}

export interface Message {
  id: string;
  thread_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  thought: string;
  thinking_duration?: string;
  actions?: AgentAction[];
  diffs?: FileDiff[];
  artifacts: Artifact[];
  attachments: Attachment[];
  memory_recalls: MemoryFact[];
  created_at: number;
  cached?: boolean;
  audio_url?: string;
  feedback?: 'positive' | 'negative' | null;
}

export interface SmbItem {
  name: string;
  relative_path: string;
  is_dir: boolean;
  size: number;
  modified_at: number;
}

export interface Workpiece3DData {
  title: string;
  format: 'openscad' | 'stl' | 'obj' | 'laser_svg';
  code?: string;
  dimensions_mm?: [number, number, number];
  material?: string;
  tolerance_mm?: number;
  kerf_mm?: number;
  layer_count?: number;
}

