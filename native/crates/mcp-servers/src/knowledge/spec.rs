use serde_json::{Value, json};

fn tool(
    name: &str,
    description: &str,
    properties: &Value,
    required: &[&str],
    read_only: bool,
) -> Value {
    json!({
        "name": name,
        "description": description,
        "inputSchema": {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": false,
        },
        "annotations": {
            "readOnlyHint": read_only,
            "destructiveHint": !read_only,
            "openWorldHint": false,
            "idempotentHint": read_only,
        },
    })
}

pub fn tools() -> Vec<Value> {
    let kinds = json!({"type": "array", "items": {"type": "string", "enum": ["person", "place", "object", "habit", "preference", "event", "concept"]}});
    vec![
        tool(
            "knowledge_search",
            "cerca nella memoria personale della persona che sta parlando, per significato e seguendo le relazioni",
            &json!({
                "text": {"type": "string"},
                "kinds": kinds,
                "limit": {"type": "integer", "minimum": 1},
                "depth": {"type": "integer", "minimum": 0},
                "household": {"type": "boolean", "description": "includi cio' che i familiari hanno condiviso"},
                "min_confidence": {"type": "integer", "minimum": 0, "maximum": 1000},
            }),
            &["text"],
            true,
        ),
        tool(
            "knowledge_neighbors",
            "elenca cio' che e' collegato a una persona, un luogo o un oggetto della memoria personale",
            &json!({
                "kind": {"type": "string", "enum": ["person", "place", "object", "habit", "preference", "event", "concept"]},
                "label": {"type": "string"},
                "relation": {"type": "string"},
                "direction": {"type": "string", "enum": ["out", "in", "both"]},
                "limit": {"type": "integer", "minimum": 1},
            }),
            &[],
            true,
        ),
        tool(
            "knowledge_learn",
            "estrae fatti da una frase detta dalla persona e li aggiunge alla sua memoria personale",
            &json!({"text": {"type": "string"}, "reference": {"type": "string"}}),
            &["text"],
            false,
        ),
        tool(
            "knowledge_observe",
            "registra che un evento e' accaduto ora: ripetuto nei giorni diventa un'abitudine",
            &json!({"label": {"type": "string"}}),
            &["label"],
            false,
        ),
        tool(
            "knowledge_correct",
            "applica una correzione esplicita della persona: asserire, smentire, rinominare, rimuovere, limitare o descrivere",
            &json!({"correction": {"type": "object"}}),
            &["correction"],
            false,
        ),
        tool(
            "knowledge_export",
            "esporta la memoria personale con i soli dati non riservati",
            &json!({}),
            &[],
            true,
        ),
    ]
}
