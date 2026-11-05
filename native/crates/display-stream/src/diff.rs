use crate::op::{MAX_DEPTH, MAX_OPS, Op};
use crate::pointer::join;
use serde_json::Value;

#[must_use]
pub fn diff(old: &Value, new: &Value) -> Option<Vec<Op>> {
    let mut ops = Vec::new();
    walk(old, new, "", 0, &mut ops);
    (ops.len() <= MAX_OPS).then_some(ops)
}

fn walk(old: &Value, new: &Value, path: &str, depth: usize, ops: &mut Vec<Op>) {
    if old == new || ops.len() > MAX_OPS {
        return;
    }
    match (old, new) {
        (Value::Object(before), Value::Object(after)) if depth < MAX_DEPTH => {
            for key in before.keys().filter(|k| !after.contains_key(*k)) {
                ops.push(Op::Remove {
                    path: join(path, key),
                });
            }
            for (key, value) in after {
                match before.get(key) {
                    Some(previous) => walk(
                        previous,
                        value,
                        &join(path, key),
                        depth.saturating_add(1),
                        ops,
                    ),
                    None => ops.push(Op::Add {
                        path: join(path, key),
                        value: value.clone(),
                    }),
                }
            }
        }
        _ => ops.push(Op::Replace {
            path: path.to_owned(),
            value: new.clone(),
        }),
    }
}
