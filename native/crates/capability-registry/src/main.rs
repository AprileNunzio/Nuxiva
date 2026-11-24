use std::collections::BTreeSet;
use std::fs::File;
use std::io::Read;
use std::path::Path;
use std::process::ExitCode;

use capability_registry::{MAX_DOCUMENT_BYTES, Registry, RegistryError};

fn read(path: &str) -> Result<Vec<u8>, RegistryError> {
    let limit = u64::try_from(MAX_DOCUMENT_BYTES)
        .unwrap_or(u64::MAX)
        .saturating_add(1);
    let mut bytes = Vec::new();
    File::open(Path::new(path))
        .and_then(|file| file.take(limit).read_to_end(&mut bytes))
        .map_err(|_| RegistryError::Invalid("read"))?;
    Ok(bytes)
}

fn run(args: &[String]) -> Result<String, RegistryError> {
    let document = args.get(2).ok_or(RegistryError::Invalid("usage"))?;
    let registry = Registry::from_document(&read(document)?)?;
    match args.get(1).map(String::as_str) {
        Some("check") => Ok(serde_json::json!({ "capabilities": registry.len() }).to_string()),
        Some("coverage") => {
            let names = args.get(3).ok_or(RegistryError::Invalid("usage"))?;
            let wanted: BTreeSet<String> = serde_json::from_slice(&read(names)?)?;
            let present: BTreeSet<String> = registry.ids().map(str::to_owned).collect();
            let missing: Vec<&String> = wanted.difference(&present).collect();
            let unknown: Vec<&String> = present.difference(&wanted).collect();
            if missing.is_empty() && unknown.is_empty() {
                Ok(serde_json::json!({ "covered": wanted.len() }).to_string())
            } else {
                Err(RegistryError::Duplicate(format!(
                    "coverage missing={} unknown={}",
                    missing.len(),
                    unknown.len()
                )))
            }
        }
        _ => Err(RegistryError::Invalid("usage")),
    }
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().collect();
    match run(&args) {
        Ok(output) => {
            println!("{output}");
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("{error}");
            ExitCode::FAILURE
        }
    }
}
