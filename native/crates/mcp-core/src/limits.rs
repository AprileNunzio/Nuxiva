#[derive(Debug, Clone, Copy)]
pub struct Ceilings;

impl Ceilings {
    pub const MESSAGE_BYTES: usize = 8 * 1024 * 1024;
    pub const PAGES: usize = 1_000;
    pub const TOOLS_PER_SERVER: usize = 10_000;
    pub const TOOLS_TOTAL: usize = 100_000;
    pub const NAME_LEN: usize = 128;
    pub const DESCRIPTION_CHARS: usize = 8_000;
    pub const SCHEMA_BYTES: usize = 1024 * 1024;
    pub const SCHEMA_DEPTH: usize = 64;
    pub const SCHEMA_NODES: usize = 200_000;
    pub const ID_TEXT: usize = 128;
    pub const METHOD_LEN: usize = 128;
    pub const ERROR_MESSAGE_CHARS: usize = 1_000;
    pub const TIMEOUT_MS: usize = 600_000;
    pub const IN_FLIGHT: usize = 4_096;
    pub const EVENT_QUEUE: usize = 65_536;
    pub const LONG_MS: usize = 86_400_000;
    pub const BREAKER_FAILURES: usize = 1_000;
    pub const JOBS: usize = 4_096;
    pub const ERROR_QUEUE: usize = 65_536;
    pub const CRITIC_KEYS: usize = 1_024;
}
