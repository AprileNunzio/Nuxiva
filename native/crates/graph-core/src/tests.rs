use crate::{
    EdgeKind, GraphError, GraphSettings, Language, MemorySource, NodeKind, build, extract, language,
};

pub(crate) fn fixture() -> MemorySource {
    let mut s = MemorySource::new();
    s.put(
        "Cargo.toml",
        "[workspace]\nmembers = [\"crates/a\", \"crates/b\"]\n",
    );
    s.put(
        "crates/a/Cargo.toml",
        "[package]\nname = \"nuxiva-a\"\n\n[dependencies]\nserde = \"1\"\n",
    );
    s.put(
        "crates/b/Cargo.toml",
        "[package]\nname = \"nuxiva-b\"\n\n[dependencies]\nnuxiva-a = { path = \"../a\" }\n\n[dev-dependencies.serde_json]\nversion = \"1\"\n",
    );
    s.put(
        "crates/a/src/lib.rs",
        "mod util;\nmod deep;\npub use util::helper;\npub fn start() {}\npub struct Engine;\n",
    );
    s.put("crates/a/src/util.rs", "use crate::deep::inner::Thing;\nuse super::deep;\npub fn helper() {}\nconst LIMIT: usize = 3;\n");
    s.put("crates/a/src/deep/mod.rs", "pub mod inner;\n");
    s.put(
        "crates/a/src/deep/inner.rs",
        "pub struct Thing;\npub trait Rule {}\n",
    );
    s.put("crates/b/src/lib.rs", "use nuxiva_a::start;\nuse std::collections::{HashMap, HashSet};\npub fn run() { start() }\n");
    s.put("app/main.py", "import os\nfrom app.tools import load, save as keep\nfrom . import tools\nfrom .missing import x\n\nLIMIT = 3\n\nclass Runner:\n    def inner(self): pass\n\nasync def go():\n    pass\n");
    s.put("app/tools.py", "def load(): pass\ndef save(): pass\n");
    s.put("app/__init__.py", "");
    s.put("web/src/index.ts", "import { a } from './util';\nimport './style.js';\nexport const VALUE = 1;\nexport function render() {}\ninterface Props {}\nconst lazy = () => import('./lazy');\nimport react from 'react';\n");
    s.put("web/src/util.ts", "export function a() {}\n");
    s.put("web/src/lazy.tsx", "export default function Lazy() {}\n");
    s.put("web/src/style.ts", "export const css = 1;\n");
    s.put(
        "agenti/x/feature.json",
        "{\"id\":\"meteo\",\"name\":\"Meteo\"}",
    );
    s.put("docs/guide.md", "# Guida\n\nVedi [util](../crates/a/src/util.rs#x) e `crates/b/src/lib.rs`.\n\n```\n# non una sezione\n```\n\n## Dettagli\n[web](https://example.com)\n");
    s.put("assets/logo.png", "binary");
    s
}

fn graph() -> crate::Graph {
    build(&fixture(), &GraphSettings::default()).expect("build")
}

fn imports(g: &crate::Graph, from: &str, to: &str) -> bool {
    let (Some(a), Some(b)) = (g.file_id(from), g.file_id(to)) else {
        return false;
    };
    g.out_edges(a)
        .any(|(d, k)| d == b && k == EdgeKind::Imports)
}

#[test]
fn rust_module_graph() {
    let g = graph();
    assert!(imports(&g, "crates/a/src/lib.rs", "crates/a/src/util.rs"));
    assert!(imports(
        &g,
        "crates/a/src/lib.rs",
        "crates/a/src/deep/mod.rs"
    ));
    assert!(imports(
        &g,
        "crates/a/src/util.rs",
        "crates/a/src/deep/inner.rs"
    ));
    assert!(imports(
        &g,
        "crates/a/src/deep/mod.rs",
        "crates/a/src/deep/inner.rs"
    ));
    assert!(imports(
        &g,
        "crates/a/src/util.rs",
        "crates/a/src/deep/mod.rs"
    ));
}

#[test]
fn python_and_script_imports() {
    let g = graph();
    assert!(imports(&g, "app/main.py", "app/tools.py"));
    assert!(!imports(&g, "app/main.py", "app/main.py"));
    assert!(imports(&g, "web/src/index.ts", "web/src/util.ts"));
    assert!(imports(&g, "web/src/index.ts", "web/src/style.ts"));
    assert!(imports(&g, "web/src/index.ts", "web/src/lazy.tsx"));
}

#[test]
fn package_dependencies_and_membership() {
    let g = graph();
    let pkg = |name: &str| {
        g.nodes()
            .iter()
            .position(|n| n.kind == NodeKind::Package && n.name == name)
            .and_then(|i| u32::try_from(i).ok())
    };
    let (a, b) = (pkg("nuxiva-a").expect("a"), pkg("nuxiva-b").expect("b"));
    assert!(
        g.out_edges(b)
            .any(|(d, k)| d == a && k == EdgeKind::DependsOn)
    );
    assert!(!g.out_edges(a).any(|(_, k)| k == EdgeKind::DependsOn));
    let lib = g.file_id("crates/b/src/lib.rs").expect("lib");
    assert!(
        g.out_edges(b)
            .any(|(d, k)| d == lib && k == EdgeKind::Declares)
    );
    assert!(
        g.out_edges(lib)
            .any(|(d, k)| d == a && k == EdgeKind::Imports)
    );
}

#[test]
fn symbols_and_sections() {
    let g = graph();
    let names = |file: &str| -> Vec<String> {
        let id = g.file_id(file).expect("file");
        g.out_edges(id)
            .filter(|(_, k)| *k == EdgeKind::Declares)
            .filter_map(|(d, _)| g.node(d).map(|n| n.name.clone()))
            .collect()
    };
    let rust = names("crates/a/src/lib.rs");
    assert!(rust.contains(&"start".to_owned()) && rust.contains(&"Engine".to_owned()));
    let py = names("app/main.py");
    assert!(
        py.contains(&"Runner".to_owned())
            && py.contains(&"go".to_owned())
            && py.contains(&"LIMIT".to_owned())
    );
    assert!(!py.contains(&"inner".to_owned()));
    assert!(names("web/src/index.ts").contains(&"VALUE".to_owned()));
    assert_eq!(
        names("agenti/x/feature.json"),
        vec!["meteo".to_owned(), "Meteo".to_owned()]
    );
    let md = names("docs/guide.md");
    assert_eq!(md, vec!["Guida".to_owned(), "Dettagli".to_owned()]);
    let section = g
        .out_edges(g.file_id("docs/guide.md").expect("md"))
        .find(|(_, k)| *k == EdgeKind::Declares)
        .and_then(|(d, _)| g.node(d))
        .expect("node");
    assert_eq!(section.kind, NodeKind::Section);
}

#[test]
fn markdown_documents_files() {
    let g = graph();
    let md = g.file_id("docs/guide.md").expect("md");
    let documented: Vec<&str> = g
        .out_edges(md)
        .filter(|(_, k)| *k == EdgeKind::Documents)
        .filter_map(|(d, _)| g.path(d))
        .collect();
    assert!(
        documented.contains(&"crates/a/src/util.rs") && documented.contains(&"crates/b/src/lib.rs")
    );
    assert_eq!(documented.len(), 2);
}

#[test]
fn inbound_matches_outbound() {
    let g = graph();
    let mut forward = 0usize;
    let mut backward = 0usize;
    for id in 0..u32::try_from(g.node_count()).expect("count") {
        forward += g.out_edges(id).count();
        backward += g.in_edges(id).count();
        for (dst, kind) in g.out_edges(id) {
            assert!(g.in_edges(dst).any(|(s, k)| s == id && k == kind));
        }
    }
    assert_eq!(forward, backward);
    assert_eq!(forward, g.edge_count());
}

#[test]
fn build_is_deterministic() {
    let a = graph();
    let b = graph();
    assert_eq!(a.stats(), b.stats());
    assert_eq!(a.nodes(), b.nodes());
    assert_eq!(a.digest(0), b.digest(0));
}

#[test]
fn digest_tracks_content() {
    let mut s = fixture();
    let before = build(&s, &GraphSettings::default()).expect("a");
    s.put("app/tools.py", "def load(): pass\n");
    let after = build(&s, &GraphSettings::default()).expect("b");
    let id = before.file_id("app/tools.py").expect("id");
    assert_ne!(before.digest(id), after.digest(id));
    let other = before.file_id("web/src/util.ts").expect("id");
    assert_eq!(before.digest(other), after.digest(other));
}

#[test]
fn hostile_paths_and_files_are_skipped() {
    let mut s = fixture();
    for bad in [
        "../escape.rs",
        "/abs.rs",
        "a//b.rs",
        "a/./b.rs",
        "a\\b.rs",
        "x/\u{0}y.rs",
        "",
    ] {
        s.put(bad, "pub fn evil() {}");
    }
    s.put_bytes("bin/latin.py", vec![0xff, 0xfe, 0x00, 0x80]);
    s.put("big/huge.rs", &"x".repeat(2 * 1024 * 1024));
    let g = build(&s, &GraphSettings::default()).expect("build");
    assert_eq!(g.stats().skipped, 9);
    assert!(g.file_id("../escape.rs").is_none());
    assert!(g.file_id("bin/latin.py").is_none());
    assert!(g.file_id("big/huge.rs").is_none());
}

#[test]
fn limits_are_enforced() {
    let settings = GraphSettings {
        max_files: 3,
        ..GraphSettings::default()
    };
    let g = build(&fixture(), &settings).expect("build");
    assert_eq!(g.file_count(), 3);
    assert!(g.stats().skipped > 0);
    let mut s = MemorySource::new();
    let body: String = (0..2_000)
        .map(|i| format!("pub fn f{i}() {{}}\nuse a::b{i};\n"))
        .collect();
    s.put("src/lib.rs", &body);
    let g = build(
        &s,
        &GraphSettings {
            max_symbols_per_file: 10,
            max_imports_per_file: 5,
            ..GraphSettings::default()
        },
    )
    .expect("build");
    assert_eq!(g.stats().symbols, 10);
}

#[test]
fn settings_validation() {
    assert!(GraphSettings::default().validate().is_ok());
    assert_eq!(
        GraphSettings::from_json("{\"max_files\":0}"),
        Err(GraphError::Settings)
    );
    assert_eq!(
        GraphSettings::from_json("{\"unknown\":1}"),
        Err(GraphError::Settings)
    );
    assert_eq!(
        GraphSettings::from_json(&" ".repeat(70_000)),
        Err(GraphError::TooLarge)
    );
    assert_eq!(
        GraphSettings::from_json("{\"max_files\":10}").map(|s| s.max_files),
        Ok(10)
    );
    assert_eq!(
        build(
            &MemorySource::new(),
            &GraphSettings {
                max_name_chars: 0,
                ..GraphSettings::default()
            }
        )
        .err(),
        Some(GraphError::Settings)
    );
}

#[test]
fn language_detection() {
    assert_eq!(language("a/Cargo.toml"), Language::Cargo);
    assert_eq!(language("a/feature.json"), Language::Manifest);
    assert_eq!(language("a/x.tsx"), Language::Script);
    assert_eq!(language("a/x.png"), Language::Other);
    assert_eq!(language("README"), Language::Other);
}

#[test]
fn rust_use_groups_expand() {
    let facts = extract(
        Language::Rust,
        "use crate::{a::{b, c as d}, e};\nuse std::io::{self, Read};\nuse x::\n    y;\n",
        &GraphSettings::default(),
    );
    assert_eq!(
        facts.imports,
        vec![
            "use:crate::a::b",
            "use:crate::a::c",
            "use:crate::e",
            "use:std::io",
            "use:std::io::Read",
            "use:x::y"
        ]
        .into_iter()
        .map(String::from)
        .collect::<Vec<_>>()
    );
}

#[test]
fn extractors_survive_garbage() {
    let mut seed = 0x9E37_79B9_7F4A_7C15_u64;
    let alphabet: Vec<char> = "use{}:;,\"'`#[]()=\n  \tfnmodimportfromdefclassfunction/.*é\u{0}"
        .chars()
        .collect();
    let settings = GraphSettings::default();
    for round in 0..400 {
        let mut text = String::new();
        for _ in 0..(round % 200) {
            seed ^= seed << 13;
            seed ^= seed >> 7;
            seed ^= seed << 17;
            let pick = usize::try_from(seed % alphabet.len() as u64).unwrap_or(0);
            text.push(alphabet.get(pick).copied().unwrap_or('x'));
        }
        for lang in [
            Language::Rust,
            Language::Python,
            Language::Script,
            Language::Cargo,
            Language::Manifest,
            Language::Markdown,
        ] {
            let facts = extract(lang, &text, &settings);
            assert!(facts.symbols.len() <= settings.max_symbols_per_file);
            assert!(facts.imports.len() <= settings.max_imports_per_file);
        }
    }
}

#[test]
fn deep_and_wide_inputs_are_bounded() {
    let nested = format!("use {}a{};", "x::{".repeat(5_000), "}".repeat(5_000));
    let facts = extract(Language::Rust, &nested, &GraphSettings::default());
    assert!(facts.imports.len() <= 512);
    let json = format!("{}1{}", "[".repeat(100_000), "]".repeat(100_000));
    assert!(
        extract(Language::Manifest, &json, &GraphSettings::default())
            .symbols
            .is_empty()
    );
}

#[test]
fn clippy_free_scale() {
    let mut s = MemorySource::new();
    for i in 0..3_000 {
        s.put(
            &format!("m{}/f{i}.py", i % 50),
            &format!("from f{} import x\ndef f{i}(): pass\n", (i + 7) % 3_000),
        );
    }
    let g = build(&s, &GraphSettings::default()).expect("build");
    assert_eq!(g.file_count(), 3_000);
    assert!(g.edge_count() > 3_000);
}

#[test]
fn rust_constants_and_const_fns() {
    let text = "const LIMIT: usize = 3;\npub const fn make() {}\npub(crate) static mut COUNT: u8 = 0;\npub async fn go() {}\n";
    let facts = extract(Language::Rust, text, &GraphSettings::default());
    let names: Vec<&str> = facts.symbols.iter().map(|f| f.name.as_str()).collect();
    assert_eq!(names, vec!["LIMIT", "make", "COUNT", "go"]);
}
