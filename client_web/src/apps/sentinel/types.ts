export interface SentinelSubject { type:'person'|'guest'|'nuxiva'|'device'|'automation'; id?:string|number; }
export interface SentinelEvent { id:string; at_ms:number; kind:string; group:string; subject:SentinelSubject; place:string|null; text:string; sensitivity:string; source:string; journey_id?:string|null; }
export interface SentinelJourney { id:string; question:string; answer:string; state:string; elapsed:number; steps:{id:number; kind:string; state:string; name:string; detail:string; start:number; end:number}[]; }
export interface SentinelPage { events:SentinelEvent[]; next:[number,string]|null; }
export interface NativeBuild { state:'building'|'restarting'|'ready'|'failed'|'disabled'|'unknown'; stage:string|null; at:number|null; }
export interface SentinelStatus { enabled:boolean; native:boolean; build?:NativeBuild; days:string[]; retention:Record<string,number>|null; }
export interface SentinelIntegrity { day:string; count:number; chain:boolean; signed:boolean|null; torn:boolean; }
export interface SentinelSummary { day:string; total:number; kinds:Record<string,number>; guests:number; integrity:SentinelIntegrity; }
