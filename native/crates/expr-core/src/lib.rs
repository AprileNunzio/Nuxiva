#![forbid(unsafe_code)]

mod builtins;
mod eval;
mod lexer;
mod parser;
mod value;

pub use eval::{MAX_ITEMS, MAX_STEPS, MAX_TEXT};
pub use value::{Value, float_repr, number, parse_number, str_repr};

pub const MAX_LEN: usize = 400;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Fault {
    Expr(String),
    Host,
}

pub trait Host {
    fn name(&mut self, name: &str) -> Result<Option<Value>, Fault>;
    fn call(&mut self, name: &str, args: Vec<Value>) -> Result<Value, Fault>;
}

pub fn evaluate<H: Host>(source: &str, host: &mut H) -> Result<Value, Fault> {
    if source.chars().count() > MAX_LEN {
        return Err(Fault::Expr("espressione troppo lunga".to_owned()));
    }
    let toks = lexer::tokenize(source.trim())?;
    let tree = parser::Parser::new(toks).parse()?;
    eval::Evaluator::new(host).eval(&tree)
}

#[cfg(test)]
mod tests;
