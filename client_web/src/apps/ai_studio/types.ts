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
  kind: 'code' | 'html' | 'svg' | 'diagram' | 'markdown';
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

export interface Message {
  id: string;
  thread_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  thought: string;
  artifacts: Artifact[];
  attachments: Attachment[];
  memory_recalls: MemoryFact[];
  created_at: number;
  cached?: boolean;
}

export interface SmbItem {
  name: string;
  relative_path: string;
  is_dir: boolean;
  size: number;
  modified_at: number;
}
