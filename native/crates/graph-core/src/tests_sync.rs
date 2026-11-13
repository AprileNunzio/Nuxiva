use crate::tests::fixture;
use crate::{Cache, GraphError, GraphSettings, MemorySource, build};

#[test]
fn first_sync_adds_everything() {
    let mut cache = Cache::new();
    let report = cache
        .sync(&fixture(), &GraphSettings::default())
        .expect("sync");
    assert_eq!(report.added, cache.len());
    assert_eq!(
        (report.changed, report.removed, report.unchanged),
        (0, 0, 0)
    );
    assert!(report.touched());
}

#[test]
fn second_sync_changes_nothing() {
    let mut cache = Cache::new();
    let source = fixture();
    let settings = GraphSettings::default();
    cache.sync(&source, &settings).expect("sync");
    let before = cache.graph().expect("graph");
    let report = cache.sync(&source, &settings).expect("sync");
    assert!(!report.touched());
    assert_eq!(report.unchanged, cache.len());
    assert_eq!(before.version(), cache.graph().expect("graph").version());
}

#[test]
fn edits_additions_and_removals_are_tracked() {
    let mut cache = Cache::new();
    let mut source = fixture();
    let settings = GraphSettings::default();
    cache.sync(&source, &settings).expect("sync");
    let before = cache.graph().expect("graph");
    source.put("app/tools.py", "def load(): pass\ndef extra(): pass\n");
    source.put("app/new.py", "import tools\n");
    source.remove("web/src/util.ts");
    let report = cache.sync(&source, &settings).expect("sync");
    assert_eq!((report.added, report.changed, report.removed), (1, 1, 1));
    let after = cache.graph().expect("graph");
    assert_ne!(before.version(), after.version());
    assert!(after.file_id("app/new.py").is_some());
    assert!(after.file_id("web/src/util.ts").is_none());
    assert_eq!(
        after.stats().files,
        build(&source, &settings).expect("full").stats().files
    );
}

#[test]
fn touched_but_identical_content_is_unchanged() {
    let mut cache = Cache::new();
    let mut source = fixture();
    let settings = GraphSettings::default();
    cache.sync(&source, &settings).expect("sync");
    source.put("app/tools.py", "def load(): pass\ndef save(): pass\n");
    let report = cache.sync(&source, &settings).expect("sync");
    assert!(!report.touched());
}

#[test]
fn incremental_graph_equals_full_rebuild() {
    let mut cache = Cache::new();
    let mut source = fixture();
    let settings = GraphSettings::default();
    cache.sync(&source, &settings).expect("sync");
    source.put(
        "crates/a/src/util.rs",
        "use crate::deep::inner::Thing;\npub fn changed() {}\n",
    );
    source.remove("app/__init__.py");
    cache.sync(&source, &settings).expect("sync");
    let incremental = cache.graph().expect("graph");
    let full = build(&source, &settings).expect("full");
    assert_eq!(incremental.version(), full.version());
    assert_eq!(incremental.nodes(), full.nodes());
    assert_eq!(incremental.edge_count(), full.edge_count());
}

#[test]
fn changing_settings_discards_stale_facts() {
    let mut cache = Cache::new();
    let source = fixture();
    cache
        .sync(&source, &GraphSettings::default())
        .expect("sync");
    let tight = GraphSettings {
        max_symbols_per_file: 1,
        ..GraphSettings::default()
    };
    let report = cache.sync(&source, &tight).expect("sync");
    assert_eq!(report.unchanged, 0);
    let full = build(&source, &GraphSettings::default()).expect("full");
    assert!(cache.graph().expect("graph").stats().symbols < full.stats().symbols);
}

#[test]
fn sealed_cache_round_trips() {
    let mut cache = Cache::new();
    let source = fixture();
    let settings = GraphSettings::default();
    cache.sync(&source, &settings).expect("sync");
    let key = [7u8; 32];
    let sealed = cache.seal(&key).expect("seal");
    assert!(!sealed.windows(5).any(|w| w == b"Engin"));
    let mut restored = Cache::open(&sealed, &key).expect("open");
    let report = restored.sync(&source, &settings).expect("sync");
    assert!(!report.touched());
    assert_eq!(
        restored.graph().expect("a").version(),
        cache.graph().expect("b").version()
    );
}

#[test]
fn sealed_cache_rejects_tampering_and_wrong_key() {
    let mut cache = Cache::new();
    cache
        .sync(&fixture(), &GraphSettings::default())
        .expect("sync");
    let key = [1u8; 32];
    let sealed = cache.seal(&key).expect("seal");
    assert_eq!(
        Cache::open(&sealed, &[2u8; 32]).err(),
        Some(GraphError::Source)
    );
    for index in [0, 24, sealed.len() / 2, sealed.len() - 1] {
        let mut broken = sealed.clone();
        if let Some(byte) = broken.get_mut(index) {
            *byte ^= 0x01;
        }
        assert_eq!(Cache::open(&broken, &key).err(), Some(GraphError::Source));
    }
    assert_eq!(
        Cache::open(sealed.get(..10).unwrap_or_default(), &key).err(),
        Some(GraphError::Source)
    );
    assert_eq!(Cache::open(&[], &key).err(), Some(GraphError::Source));
    assert_ne!(cache.seal(&key).expect("again"), sealed);
}

#[test]
fn empty_source_gives_empty_graph() {
    let graph = build(&MemorySource::new(), &GraphSettings::default()).expect("build");
    assert_eq!((graph.node_count(), graph.edge_count()), (0, 0));
}
