use std::collections::BTreeMap;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Failure {
    Retryable,
    Permanent,
    NotStarted,
}

#[derive(Debug)]
pub struct Call<'a> {
    pub capability: &'a str,
    pub key: &'a str,
    pub args: &'a BTreeMap<String, String>,
}

pub trait Invoker {
    fn invoke(&mut self, call: &Call<'_>) -> Result<String, Failure>;
}

pub trait ApprovalGate {
    fn approve(&mut self, step: &str, capability: &str, args: &BTreeMap<String, String>) -> bool;
}

pub trait Cancel {
    fn cancelled(&self) -> bool;
}

#[derive(Debug, Default, Clone, Copy)]
pub struct Never;

impl Cancel for Never {
    fn cancelled(&self) -> bool {
        false
    }
}
