export interface RolloutNode {
  id: string;
  name: string;
  tier: string;
  ip: string;
  current_version: string;
  target_version: string;
  status: 'ready' | 'pending' | 'precaching' | 'updating' | 'complete' | 'failed' | 'rolled_back';
  collaudo_passed: boolean;
}

export interface CollaudoTest {
  id: string;
  name: string;
  status: 'PASS' | 'WARN' | 'FAIL';
  metric: string;
  passed: boolean;
  detail: string;
}

export interface CollaudoResult {
  timestamp: number;
  all_passed: boolean;
  tests: CollaudoTest[];
}

export interface UpdateLog {
  timestamp: number;
  level: string;
  message: string;
}

export interface UpdateStatus {
  current_version: string;
  latest_version: string;
  update_available: boolean;
  last_check_ts: number;
  scheduled_time: string;
  synchronized: boolean;
  auto_rollback: boolean;
  channel: string;
  status: string;
  nodes: RolloutNode[];
  logs: UpdateLog[];
}
