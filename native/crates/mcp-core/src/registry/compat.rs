use std::collections::HashSet;

use serde_json::{Map, Value};

use crate::protocol::ToolSpec;

fn object(value: &Value) -> Option<&Map<String, Value>> {
    value.as_object()
}

fn required(map: &Map<String, Value>) -> HashSet<&str> {
    map.get("required")
        .and_then(Value::as_array)
        .map(|items| items.iter().filter_map(Value::as_str).collect())
        .unwrap_or_default()
}

fn properties_extend(old: &Map<String, Value>, new: &Map<String, Value>) -> bool {
    let empty = Map::new();
    let old_props = old.get("properties").and_then(object).unwrap_or(&empty);
    let new_props = new.get("properties").and_then(object).unwrap_or(&empty);
    old_props
        .iter()
        .all(|(key, definition)| new_props.get(key) == Some(definition))
}

fn other_keys_equal(old: &Map<String, Value>, new: &Map<String, Value>) -> bool {
    let skip = |key: &&String| !matches!(key.as_str(), "properties" | "required");
    let old_keys: HashSet<&String> = old.keys().filter(skip).collect();
    let new_keys: HashSet<&String> = new.keys().filter(skip).collect();
    old_keys == new_keys && old_keys.iter().all(|key| old.get(*key) == new.get(*key))
}

#[must_use]
pub fn compatible(old: &ToolSpec, new: &ToolSpec) -> bool {
    if old.description != new.description
        || old.title != new.title
        || old.annotations != new.annotations
        || old.output_schema != new.output_schema
    {
        return false;
    }
    let (Some(old_schema), Some(new_schema)) =
        (object(&old.input_schema), object(&new.input_schema))
    else {
        return false;
    };
    properties_extend(old_schema, new_schema)
        && required(new_schema).is_subset(&required(old_schema))
        && other_keys_equal(old_schema, new_schema)
}
