use std::sync::Arc;

use serde_json::{Value, json};

use crate::tests::get;
use crate::{KnowledgeSettings, MasterKey, Service};

#[test]
fn parallel_readers_and_writers_stay_consistent() {
    let service = Arc::new(
        Service::new(
            KnowledgeSettings::default(),
            Some(Arc::new(MasterKey::from_key([3; 32]))),
            None,
            Arc::new(|| 1_800_000_000_000),
            false,
        )
        .unwrap_or_else(|_| unreachable!("service")),
    );
    let reg = json!({"op": "register", "id": "nunzio", "name": "Nunzio", "role": "family"});
    assert!(service.handle(&reg.to_string()).contains("true"));
    let handles: Vec<_> = (0..8_u32)
        .map(|t| {
            let s = Arc::clone(&service);
            std::thread::spawn(move || {
                for i in 0..100_u32 {
                    let write = json!({"op": "remember", "as": "nunzio", "kind": "object", "label": format!("cosa {t} {i}")});
                    let _ = s.handle(&write.to_string());
                    let read = json!({"op": "search", "as": "nunzio", "query": {"text": "cosa"}});
                    let _ = s.handle(&read.to_string());
                }
            })
        })
        .collect();
    for handle in handles {
        assert!(handle.join().is_ok());
    }
    let stats: Value =
        serde_json::from_str(&service.handle(&json!({"op": "stats", "as": "nunzio"}).to_string()))
            .unwrap_or(Value::Null);
    assert_eq!(get(&stats, "/data/nodes"), 800);
}
