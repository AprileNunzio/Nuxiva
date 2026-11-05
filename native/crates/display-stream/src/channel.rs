use crate::diff::diff;
use crate::op::Op;
use nuxiva_display_domain::Version;
use serde::Serialize;
use serde_json::Value;

#[derive(Debug, Clone, PartialEq, Serialize)]
#[serde(tag = "t", rename_all = "lowercase")]
pub enum Frame {
    Full { v: Version, s: Value },
    Patch { f: Version, v: Version, p: Vec<Op> },
}

#[derive(Debug, Default)]
pub struct Channel {
    version: Version,
    value: Option<Value>,
}

impl Channel {
    #[must_use]
    pub const fn new() -> Self {
        Self {
            version: Version(0),
            value: None,
        }
    }

    #[must_use]
    pub const fn version(&self) -> Version {
        self.version
    }

    pub fn publish(&mut self, next: Value) -> Option<Frame> {
        let frame = match &self.value {
            Some(previous) if *previous == next => return None,
            Some(previous) => {
                let from = self.version;
                let to = from.next();
                match diff(previous, &next) {
                    Some(ops) => Frame::Patch {
                        f: from,
                        v: to,
                        p: ops,
                    },
                    None => Frame::Full {
                        v: to,
                        s: next.clone(),
                    },
                }
            }
            None => Frame::Full {
                v: self.version.next(),
                s: next.clone(),
            },
        };
        self.version = self.version.next();
        self.value = Some(next);
        Some(frame)
    }

    #[must_use]
    pub fn full(&self) -> Option<Frame> {
        self.value.as_ref().map(|s| Frame::Full {
            v: self.version,
            s: s.clone(),
        })
    }
}
