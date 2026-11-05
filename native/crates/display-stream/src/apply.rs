use crate::error::StreamError;
use crate::op::{MAX_OPS, Op};
use crate::pointer::split;
use serde_json::{Map, Value};

pub fn apply(doc: &mut Value, ops: &[Op]) -> Result<(), StreamError> {
    if ops.len() > MAX_OPS {
        return Err(StreamError::TooManyOps);
    }
    for op in ops {
        one(doc, op)?;
    }
    Ok(())
}

fn one(doc: &mut Value, op: &Op) -> Result<(), StreamError> {
    let mut tokens = split(op.path())?;
    let Some(last) = tokens.pop() else {
        return match op {
            Op::Add { value, .. } | Op::Replace { value, .. } => {
                *doc = value.clone();
                Ok(())
            }
            Op::Remove { .. } => Err(StreamError::Pointer),
        };
    };
    let parent = descend(doc, &tokens)?;
    match op {
        Op::Add { value, .. } => {
            parent.insert(last, value.clone());
            Ok(())
        }
        Op::Replace { value, .. } => {
            let slot = parent.get_mut(&last).ok_or(StreamError::Missing)?;
            *slot = value.clone();
            Ok(())
        }
        Op::Remove { .. } => parent.remove(&last).map(|_| ()).ok_or(StreamError::Missing),
    }
}

fn descend<'a>(
    doc: &'a mut Value,
    tokens: &[String],
) -> Result<&'a mut Map<String, Value>, StreamError> {
    let mut node = doc;
    for token in tokens {
        node = node
            .as_object_mut()
            .ok_or(StreamError::NotObject)?
            .get_mut(token)
            .ok_or(StreamError::Missing)?;
    }
    node.as_object_mut().ok_or(StreamError::NotObject)
}
