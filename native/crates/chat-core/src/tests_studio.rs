use crate::artifact::ArtifactParser;
use crate::engine::ChatStudioEngine;
use crate::memory::CrossMemoryVault;
use crate::smb::{SmbGuardError, SmbPathGuard, SmbShareCategory};
use crate::types::{MemorySource, Message, Role};

#[test]
fn test_smb_path_guard_safe() {
    let guard = SmbPathGuard::new("/srv/nuxiva/condivisa");
    let resolved = guard
        .resolve_safe_path(SmbShareCategory::Documenti, "report.pdf")
        .expect("safe path");
    assert_eq!(
        resolved.to_str().expect("str"),
        "/srv/nuxiva/condivisa/01 Documenti/report.pdf"
    );

    let unc = SmbPathGuard::format_unc("192.168.1.100", SmbShareCategory::Codice, "src/main.rs");
    assert_eq!(
        unc,
        "\\\\192.168.1.100\\\\condivisa\\\\04 Codice\\src\\main.rs"
    );
}

#[test]
fn test_smb_path_guard_traversal_blocked() {
    let guard = SmbPathGuard::new("/srv/nuxiva/condivisa");
    let err = guard.resolve_safe_path(SmbShareCategory::Documenti, "../etc/shadow");
    assert_eq!(err, Err(SmbGuardError::PathTraversalDetected));

    let err2 = guard.resolve_safe_path(SmbShareCategory::Scambio, "invalid*name?.txt");
    assert_eq!(err2, Err(SmbGuardError::InvalidCharacters));
}

#[test]
fn test_artifact_parser_extraction() {
    let parser = ArtifactParser::new();
    let text = "Ecco il codice richiesto:\n```rust filename=main.rs\nfn main() {}\n```\nFine.";
    let artifacts = parser.extract(text);
    assert_eq!(artifacts.len(), 1);
    let Some(art) = artifacts.first() else {
        panic!("missing artifact");
    };
    assert_eq!(art.title, "main.rs");
    assert_eq!(art.language.as_deref(), Some("rust"));
    assert_eq!(art.kind, "code");
    assert_eq!(art.content, "fn main() {}");
}

#[test]
fn test_cross_memory_vault_voice_and_written() {
    let mut vault = CrossMemoryVault::new();
    let fact_voice = vault.learn_statement(
        "Ricorda che preferisco risposte concise e senza preamboli",
        MemorySource::VoiceSpeech,
        1000,
    );
    assert!(fact_voice.is_some());

    let fact_written = vault.learn_statement(
        "Il mio progetto principale è la domotica di casa",
        MemorySource::WrittenChat,
        2000,
    );
    assert!(fact_written.is_some());

    let recalled = vault.recall_relevant("progetto domotica", 5);
    assert!(!recalled.is_empty());
    assert!(recalled.iter().any(|f| f.value.contains("domotica")));

    let prompt = vault.build_system_injection("domotica");
    assert!(prompt.is_some());
    let prompt_str = prompt.expect("prompt");
    assert!(prompt_str.contains("RECALLED_CROSS_SESSION_MEMORY:"));
}

#[test]
fn test_chat_studio_engine_lifecycle() {
    let mut engine = ChatStudioEngine::new();
    let project = engine.create_project(
        "proj_1".to_string(),
        "Studio AI".to_string(),
        "Sviluppare interfaccia".to_string(),
        "Sii preciso".to_string(),
        "09 Progetti/StudioAI".to_string(),
        100,
    );
    assert_eq!(project.id, "proj_1");

    let thread = engine.create_thread(
        "th_1".to_string(),
        Some("proj_1".to_string()),
        "Discussione iniziale".to_string(),
        "nuxiva-core".to_string(),
        110,
    );
    assert_eq!(thread.id, "th_1");

    let msg = Message {
        id: "msg_1".to_string(),
        thread_id: "th_1".to_string(),
        role: Role::Assistant,
        content: "Ecco la preview:\n```html\n<div>Hello</div>\n```".to_string(),
        thought: Some("Ragiono sulla UI".to_string()),
        attachments: Vec::new(),
        artifacts: Vec::new(),
        memory_recalls: Vec::new(),
        created_at_ms: 120,
    };

    let processed = engine.append_message(msg, 120);
    assert_eq!(processed.artifacts.len(), 1);
    assert_eq!(processed.artifacts[0].kind, "ui_component");
    assert_eq!(engine.get_messages("th_1").len(), 1);
}
