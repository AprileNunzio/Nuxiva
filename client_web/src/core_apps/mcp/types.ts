export interface McpMetrics {
  readonly servers: number;
  readonly healthy: number;
  readonly tools: number;
  readonly active: number;
  readonly pending_approval: number;
  readonly quarantined_servers: number;
  readonly running_jobs: number;
  readonly tools_version: number;
}

export interface McpServer {
  readonly id: string;
  readonly health: 'disconnected' | 'connecting' | 'ready' | 'degraded' | 'quarantined';
  readonly tools: number;
  readonly attempts: number;
  readonly last_error: string | null;
  readonly max_risk: string;
}

export interface McpArea {
  readonly server: string;
  readonly tools: number;
  readonly mode: 'mcp' | 'legacy';
}

export interface McpStatus {
  readonly metrics: McpMetrics;
  readonly servers: readonly McpServer[];
  readonly quarantined: readonly string[];
  readonly areas: readonly McpArea[];
}

export interface McpTool {
  readonly id: string;
  readonly server: string;
  readonly name: string;
  readonly title: string | null;
  readonly description: string | null;
  readonly risk: string;
  readonly state: 'active' | 'stale' | 'quarantined';
  readonly hash: string;
}

export interface McpAuditRecord {
  readonly seq: number;
  readonly hash: string;
  readonly event: {
    readonly ts_ms: number;
    readonly agent: string;
    readonly server: string;
    readonly tool: string;
    readonly risk: string;
    readonly verdict: 'completed' | 'denied' | 'failed' | 'timed_out';
    readonly duration_ms: number;
  };
}

export interface McpAudit {
  readonly intact: boolean;
  readonly error: string | null;
  readonly count: number;
  readonly head: string;
  readonly records: readonly McpAuditRecord[];
}
