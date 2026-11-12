export interface LogEntry { id:string;timestamp:number|null;source:string;severity:string;severity_source:string;message:string; }
export interface LogSource { id:string;kind:string;name:string;available:boolean;state?:string;description?:string; }
export interface LogCatalog { sources:LogSource[];scope:string;node_id:string;local_node_id:string|null;hostname:string;warnings:string[];remote_logs_supported:boolean; }
export interface LogResult { entries:LogEntry[];counts:Record<string,number>;analysis:{code:string;occurrences:number}[];sampled:number;limit_reached:boolean;source:string;node_id:string;scope:string;phase:string|null;untimed_count:number;generated_at:string;warnings:string[];redacted:boolean; }
