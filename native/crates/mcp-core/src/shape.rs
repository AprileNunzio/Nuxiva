use serde_json::Value;

#[must_use]
pub fn depth(value: &Value) -> usize {
    let mut stack: Vec<(&Value, usize)> = vec![(value, 1)];
    let mut deepest = 0usize;
    while let Some((node, level)) = stack.pop() {
        deepest = deepest.max(level);
        let next = level.saturating_add(1);
        match node {
            Value::Array(items) => stack.extend(items.iter().map(|item| (item, next))),
            Value::Object(map) => stack.extend(map.values().map(|item| (item, next))),
            _ => {}
        }
    }
    deepest
}

#[must_use]
pub fn node_count(value: &Value) -> usize {
    let mut stack: Vec<&Value> = vec![value];
    let mut count = 0usize;
    while let Some(node) = stack.pop() {
        count = count.saturating_add(1);
        match node {
            Value::Array(items) => stack.extend(items.iter()),
            Value::Object(map) => stack.extend(map.values()),
            _ => {}
        }
    }
    count
}
