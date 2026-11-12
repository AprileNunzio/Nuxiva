export interface SentinelSubject { type:'person'|'guest'|'nuxiva'|'device'|'automation'; id?:string|number; }
export interface SentinelEvent { id:string; at_ms:number; kind:string; group:string; subject:SentinelSubject; place:string|null; text:string; sensitivity:string; source:string; journey_id?:string|null; }
export interface SentinelJourney { id:string; question:string; answer:string; state:string; elapsed:number; steps:{id:number; kind:string; state:string; name:string; detail:string; start:number; end:number}[]; }
export interface SentinelPage { events:SentinelEvent[]; next:[number,string]|null; }
export interface NativeBuild { state:'building'|'restarting'|'ready'|'failed'|'disabled'|'unknown'; stage:string|null; at:number|null; }
export interface SentinelStatus { enabled:boolean; native:boolean; build?:NativeBuild; days:string[]; retention:Record<string,number>|null; }
export interface SentinelIntegrity { day:string; count:number; chain:boolean; signed:boolean|null; torn:boolean; }
export interface SentinelSummary { day:string; total:number; kinds:Record<string,number>; guests:number; integrity:SentinelIntegrity; }
export interface NvrCameraAudio { camera:string; name:string; room:string; opted_in:boolean; private:boolean; allowed:boolean; reason:'allowed'|'private_room'|'notice_off'|'not_opted_in'; }
export interface NvrNoticeEntry { at_ms:number; places:string[]; spoken:boolean; text:string; }
export interface NvrPrivacy { notice_enabled:boolean; notice_repeat_hours:number; private_rooms:string[]; cameras:NvrCameraAudio[]; recording_audio:string[]; notice:{places:string[]; last_spoken_ms:number; pending:boolean; history:NvrNoticeEntry[]}; }
export interface NvrFindHit { kind:string; camera:string; segment:string|null; at_ms:number; text:string; speaker?:string|null; speaker_name?:string; voice?:string|null; }
export interface NvrFind { speech:NvrFindHit[]; events:NvrFindHit[]; cameras:Record<string,{name:string;room:string}>; }
export interface PrivacyProfile { slug:string; name:string; consent_voice:boolean; has_voiceprint:boolean; }
export interface NvrErase { slug:string; turns_removed:number; segments_touched:number; segments_deleted:number; }
