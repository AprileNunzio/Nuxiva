#![forbid(unsafe_code)]

mod envfile;
mod error;
mod https;
mod identity;
mod origin;
mod percent;
mod ratelimit;
mod session;
mod text;

pub use envfile::{EnvEntry, decode_value, entries, format_line, normalize};
pub use error::{GuardError, GuardResult};
pub use https::{RedirectRequest, redirect_target, safe_host};
pub use identity::{DEFAULT_NAME, MAX_NAME_LENGTH, normalize_name};
pub use origin::{
    OriginRequest, OriginVerdict, authority_hostname, host_allowed, origin_hostname, verdict,
};
pub use ratelimit::{LoginLimiter, MAX_ATTEMPTS, MAX_TRACKED, WINDOW_SECONDS};
pub use session::{MAX_TOKEN, MAX_USERNAME, MIN_SECRET, SESSION_TTL, SessionCodec};
pub use text::{py_strip, split_lines};

#[cfg(test)]
mod tests;
