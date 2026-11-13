use serde_json::{Value, json};

fn tool(name: &str, description: &str, properties: &Value, required: &[&str]) -> Value {
    json!({
        "name": name,
        "description": description,
        "inputSchema": {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": false,
        },
        "annotations": {"readOnlyHint": true, "destructiveHint": false, "openWorldHint": false, "idempotentHint": true},
    })
}

pub fn tools() -> Vec<Value> {
    let reach = json!({
        "target": {"type": "string", "description": "percorso del file, nome del pacchetto o nome di un simbolo univoco"},
        "depth": {"type": "integer", "minimum": 1, "description": "profondita' massima"},
    });
    vec![
        tool(
            "graph_sync",
            "aggiorna la mappa del progetto rileggendo solo i file cambiati",
            &json!({}),
            &[],
        ),
        tool(
            "graph_locate",
            "cerca file, pacchetti, funzioni e sezioni per nome",
            &json!({"query": {"type": "string", "description": "testo da cercare"}}),
            &["query"],
        ),
        tool(
            "graph_neighbors",
            "mostra cosa e' collegato a un elemento, in entrambe le direzioni",
            &reach,
            &["target"],
        ),
        tool(
            "graph_impact",
            "elenca cosa dipende da un elemento: va consultato prima di modificarlo",
            &reach,
            &["target"],
        ),
        tool(
            "graph_path",
            "trova il percorso piu' breve di collegamenti tra due elementi",
            &json!({"from": {"type": "string"}, "to": {"type": "string"}}),
            &["from", "to"],
        ),
        tool(
            "graph_pack",
            "riassume in poche righe simboli, dipendenze e dipendenti dei file indicati",
            &json!({
                "targets": {"type": "array", "items": {"type": "string"}, "description": "file o simboli di interesse"},
                "budget": {"type": "integer", "minimum": 1, "description": "caratteri massimi"},
            }),
            &["targets"],
        ),
    ]
}
