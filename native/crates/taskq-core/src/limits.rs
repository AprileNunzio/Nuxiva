#[derive(Debug, Clone, Copy)]
pub struct Ceilings;

impl Ceilings {
    pub const PAYLOAD_BYTES: usize = 256 * 1024;
    pub const IDENT: usize = 128;
    pub const KIND: usize = 32;
    pub const DEPS: usize = 64;
    pub const SCOPE: usize = 64;
    pub const INPUT_REF: usize = 512;
    pub const EVIDENCE: usize = 64;
    pub const QUEUE: usize = 1_000_000;
    pub const THREADS: usize = 64;
    pub const TIME_MS: u64 = 86_400_000;
    pub const TOKENS: u64 = 10_000_000;
    pub const TOOL_CALLS: u64 = 10_000;
    pub const RETRIES: u32 = 16;
    pub const RETAIN: usize = 1_000_000;
    pub const EVENT_LOG: usize = 1_000_000;
    pub const JOURNAL_BYTES: u64 = 1 << 32;
}
