mod intents;
mod patterns;
mod strict;

#[cfg(test)]
mod tests;

#[cfg(test)]
mod tests_strict;

pub use intents::{CONVERSATION, Intent, IntentError, IntentTable};
pub use strict::{Outcome, StrictReply};
