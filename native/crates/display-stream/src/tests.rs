use crate::{Channel, Frame, Op, StreamError, apply, diff};
use serde_json::{Value, json};

fn roundtrip(old: &Value, new: &Value) {
    let ops = diff(old, new).unwrap_or_default();
    let mut doc = old.clone();
    assert_eq!(apply(&mut doc, &ops), Ok(()));
    assert_eq!(&doc, new);
}

#[test]
fn identical_documents_need_no_ops() {
    let doc = json!({"a": 1, "b": {"c": [1, 2]}});
    assert_eq!(diff(&doc, &doc), Some(Vec::new()));
}

#[test]
fn changes_are_minimal_and_reversible() {
    let old = json!({"a": 1, "b": {"c": 2, "d": 3}, "gone": true});
    let new = json!({"a": 1, "b": {"c": 5, "d": 3}, "added": null});
    let ops = diff(&old, &new).unwrap_or_default();
    assert_eq!(ops.len(), 3);
    roundtrip(&old, &new);
}

#[test]
fn null_values_are_kept_distinct_from_missing_keys() {
    roundtrip(&json!({"a": 1}), &json!({"a": null}));
    roundtrip(&json!({"a": null}), &json!({}));
}

#[test]
fn arrays_and_type_changes_are_replaced_whole() {
    roundtrip(&json!({"a": [1, 2, 3]}), &json!({"a": [1, 3]}));
    roundtrip(&json!({"a": {"x": 1}}), &json!({"a": "text"}));
    roundtrip(&json!([1]), &json!({"a": 1}));
}

#[test]
fn keys_with_slashes_and_tildes_are_escaped() {
    roundtrip(&json!({"a/b": 1, "c~d": 2}), &json!({"a/b": 3, "c~d": 4}));
}

#[test]
fn bad_pointers_are_rejected() {
    let mut doc = json!({"a": 1});
    let bad = [Op::Remove { path: "a".into() }];
    assert_eq!(apply(&mut doc, &bad), Err(StreamError::Pointer));
    let missing = [Op::Replace {
        path: "/x/y".into(),
        value: json!(1),
    }];
    assert_eq!(apply(&mut doc, &missing), Err(StreamError::Missing));
    let tilde = [Op::Add {
        path: "/a~2".into(),
        value: json!(1),
    }];
    assert_eq!(apply(&mut doc, &tilde), Err(StreamError::Pointer));
}

#[test]
fn too_deep_pointers_are_rejected() {
    let mut doc = json!({});
    let path = "/a".repeat(40);
    assert_eq!(
        apply(
            &mut doc,
            &[Op::Add {
                path,
                value: json!(1)
            }]
        ),
        Err(StreamError::TooDeep)
    );
}

#[test]
fn channels_send_a_full_frame_then_patches() {
    let mut channel = Channel::new();
    assert!(matches!(
        channel.publish(json!({"a": 1})),
        Some(Frame::Full { .. })
    ));
    assert_eq!(channel.publish(json!({"a": 1})), None);
    let frame = channel.publish(json!({"a": 2}));
    assert!(
        matches!(&frame, Some(Frame::Patch { f, v, p }) if f.0 == 1 && v.0 == 2 && p.len() == 1)
    );
    assert!(matches!(channel.full(), Some(Frame::Full { .. })));
}

#[test]
fn ops_serialize_as_json_patch() {
    let op = Op::Replace {
        path: "/a".into(),
        value: json!(2),
    };
    assert_eq!(
        serde_json::to_value(&op).ok(),
        Some(json!({"op": "replace", "path": "/a", "value": 2}))
    );
}
