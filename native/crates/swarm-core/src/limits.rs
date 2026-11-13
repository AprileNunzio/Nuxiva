#[derive(Debug, Clone, Copy)]
pub struct Ceilings;

impl Ceilings {
    pub const PAYLOAD_BYTES: usize = 4 * 1024 * 1024;
    pub const TEXT_CHARS: usize = 1_000_000;
    pub const PRESENCE: usize = 256;
    pub const STEPS: usize = 512;
    pub const EDGES: usize = 4_096;
    pub const REDELEGATION_DEPTH: usize = 8;
    pub const WORKERS: usize = 4_096;
    pub const TOKENS: u64 = 10_000_000;
    pub const TOOL_CALLS: u64 = 10_000;
    pub const TIME_MS: u64 = 86_400_000;
    pub const GRAPH_TTL_MS: u64 = 86_400_000;
    pub const EVIDENCE: usize = 256;
    pub const OUTPUT_BYTES: usize = 2 * 1024 * 1024;
    pub const IDENT: usize = 128;
    pub const KIND: usize = 32;
    pub const INTENTS_PER_AGENT: usize = 64;
}
