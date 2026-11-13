use serde_json::{Value, json};

#[derive(Clone, Copy)]
enum Kind {
    Read,
    Content,
    Write,
    Remove,
}

fn tool(name: &str, description: &str, properties: &Value, required: &[&str], kind: Kind) -> Value {
    let (read_only, destructive, open_world) = match kind {
        Kind::Read => (true, false, false),
        Kind::Content => (true, false, true),
        Kind::Write => (false, false, false),
        Kind::Remove => (false, true, false),
    };
    json!({
        "name": name,
        "description": description,
        "inputSchema": {"type": "object", "properties": properties, "required": required, "additionalProperties": false},
        "annotations": {"readOnlyHint": read_only, "destructiveHint": destructive, "openWorldHint": open_world, "idempotentHint": read_only},
    })
}

pub fn tools(taint_reads: bool) -> Vec<Value> {
    let reading = if taint_reads {
        Kind::Content
    } else {
        Kind::Read
    };
    let path = json!({"path": {"type": "string", "description": "percorso"}});
    let pair = json!({"src": {"type": "string"}, "dst": {"type": "string"}});
    vec![
        tool(
            "list_dir",
            "elenca il contenuto di una cartella (vuoto = cartella di lavoro)",
            &path,
            &[],
            reading,
        ),
        tool(
            "read_file",
            "legge un file di testo",
            &path,
            &["path"],
            reading,
        ),
        tool(
            "file_info",
            "dimensione e data di un file",
            &path,
            &["path"],
            Kind::Read,
        ),
        tool(
            "find_files",
            "cerca file e cartelle per nome, senza distinguere maiuscole",
            &json!({"pattern": {"type": "string", "description": "nome o schema"}, "root": {"type": "string", "description": "cartella"}}),
            &["pattern"],
            reading,
        ),
        tool(
            "write_file",
            "crea o riscrive un file di testo; la versione precedente va nel cestino",
            &json!({"path": {"type": "string"}, "content": {"type": "string"}, "append": {"type": "boolean"}}),
            &["path", "content"],
            Kind::Write,
        ),
        tool(
            "make_dir",
            "crea una cartella, anche annidata",
            &path,
            &["path"],
            Kind::Write,
        ),
        tool(
            "copy",
            "copia un file o una cartella",
            &pair,
            &["src", "dst"],
            Kind::Write,
        ),
        tool(
            "move",
            "sposta o rinomina un file o una cartella",
            &pair,
            &["src", "dst"],
            Kind::Write,
        ),
        tool(
            "delete",
            "sposta un file o una cartella nel cestino, recuperabile",
            &path,
            &["path"],
            Kind::Remove,
        ),
    ]
}
