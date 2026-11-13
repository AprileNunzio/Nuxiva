#![forbid(unsafe_code)]

mod audit;
mod backoff;
mod connect;
mod discovery;
mod error;
mod guard;
mod health;
mod hub;
mod internal;
mod keystore;
mod limits;
mod normalize;
mod policy;
mod protocol;
mod registry;
mod runner;
mod schema;
mod session;
mod settings;
mod shape;
mod text;
mod transport;
mod trust;

pub use audit::{
    AuditChain, AuditEvent, AuditRecord, AuditSink, FileSink, GENESIS, MemorySink, Verdict,
    hash_value, resume_from_file, verify as verify_audit,
};
pub use backoff::{Backoff, Breaker};
pub use connect::connect_server;
pub use discovery::{build_entries, discover};
pub use error::{McpError, McpResult};
pub use guard::{IpClass, NetworkPolicy, Target, admit, classify_ip, parse_target, resolve};
pub use health::{Health, ServerStatus};
pub use hub::{CallOutput, Hub, ServerView, ToolView};
pub use internal::{Factory, InternalRegistry, ToolOutput, ToolServer, serve};
pub use keystore::{MemorySecrets, Secret, SecretProvider, SharedSecrets, bearer_header};
pub use limits::Ceilings;
pub use normalize::{canonical_name, valid_server_id};
pub use policy::{
    CallRequest, ConsentKey, ConsentLedger, ExternalData, Gate, PolicyConfig, RateConfig,
    RateLimiter, Risk, RiskRule, RuleField, Scope, TaintLedger, classify, glob_match, wrap_result,
};
pub use protocol::{
    CallToolResult, Content, ErrorObject, Feature, Id, Implementation, InitializeResult,
    ListChanged, Message, Notification, Outcome, Request, ResourceCaps, Response,
    ServerCapabilities, ToolSpec, VersionProfile, cancelled_notification, initialize_request,
    initialized_notification, negotiate, parse_call_result, parse_initialize_result, parse_tool,
    parse_tools_page, ping_request, supported_versions, tools_call_request, tools_list_request,
};
pub use registry::{Diff, Registry, Snapshot, ToolEntry, ToolState, compatible};
pub use runner::{Classifier, ServerHandle, SessionSlot, spawn_server};
pub use schema::CompiledSchema;
pub use session::{Session, ToolListing};
pub use settings::{ChangePolicy, Settings};
pub use shape::{depth, node_count};
pub use text::sanitize_text;
pub use transport::{HttpConfig, Link, QUEUE, SseParser, StdioSpec, pair, spawn_http, spawn_stdio};
pub use trust::{
    Catalog, Isolation, ServerEntry, SignedCatalog, TransportSpec, generate_signing_key,
    sign_catalog, verify_catalog,
};

#[cfg(test)]
mod tests;
