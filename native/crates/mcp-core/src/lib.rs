#![forbid(unsafe_code)]

mod backoff;
mod discovery;
mod error;
mod health;
mod limits;
mod normalize;
mod protocol;
mod registry;
mod runner;
mod schema;
mod session;
mod settings;
mod shape;
mod text;
mod transport;

pub use backoff::{Backoff, Breaker};
pub use discovery::{build_entries, discover};
pub use error::{McpError, McpResult};
pub use health::{Health, ServerStatus};
pub use limits::Ceilings;
pub use normalize::{canonical_name, valid_server_id};
pub use protocol::{
    CallToolResult, Content, ErrorObject, Feature, Id, Implementation, InitializeResult,
    ListChanged, Message, Notification, Outcome, Request, ResourceCaps, Response,
    ServerCapabilities, ToolSpec, VersionProfile, cancelled_notification, initialize_request,
    initialized_notification, negotiate, parse_call_result, parse_initialize_result, parse_tool,
    parse_tools_page, ping_request, supported_versions, tools_call_request, tools_list_request,
};
pub use registry::{Diff, Registry, Snapshot, ToolEntry, ToolState, compatible};
pub use runner::{ServerHandle, spawn_server};
pub use schema::CompiledSchema;
pub use session::{Session, ToolListing};
pub use settings::{ChangePolicy, Settings};
pub use shape::{depth, node_count};
pub use text::sanitize_text;
pub use transport::{HttpConfig, Link, QUEUE, SseParser, StdioSpec, pair, spawn_http, spawn_stdio};

#[cfg(test)]
mod tests;
