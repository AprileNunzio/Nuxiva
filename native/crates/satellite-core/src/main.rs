use std::path::{Path, PathBuf};
use std::process::{Command, ExitCode};
use std::time::Duration;

use nuxiva_satellite::agent::{self, Exit, Runner, service};
use nuxiva_satellite::backends::{EXTENSIONS_DIR, builtin, load_extensions, merge};
use nuxiva_satellite::link::{EnrollFile, Link, node_id, now, redeem};
use nuxiva_satellite::plan::plan;
use nuxiva_satellite::probe::profile;
use nuxiva_satellite::probe::root::Root;
use nuxiva_satellite::vault::{Vault, shred};

const STATE_DIR: &str = "/var/lib/nuxiva-satellite";
const NODE_TYPES: &[&str] = &[
    "satellite",
    "display",
    "sensor",
    "esp32",
    "android",
    "other",
];
const USAGE: &str = "uso: nuxiva-satellite probe [--root DIR] | enroll --file F [--name N] [--type T] | run | forget | install-service --file F [--name N] [--type T] [--room R]";

#[derive(Debug, Default)]
struct Args {
    command: String,
    root: Option<PathBuf>,
    file: Option<PathBuf>,
    name: Option<String>,
    kind: Option<String>,
    room: Option<String>,
}

fn parse_args() -> Result<Args, String> {
    let mut raw = std::env::args().skip(1);
    let mut args = Args {
        command: raw.next().unwrap_or_default(),
        ..Args::default()
    };
    while let Some(flag) = raw.next() {
        let value = raw
            .next()
            .ok_or_else(|| format!("manca il valore di {flag}"))?;
        match flag.as_str() {
            "--root" => args.root = Some(PathBuf::from(value)),
            "--file" => args.file = Some(PathBuf::from(value)),
            "--name" => args.name = Some(value),
            "--type" => args.kind = Some(value),
            "--room" => args.room = Some(value),
            _ => return Err(format!("opzione sconosciuta: {flag}")),
        }
    }
    Ok(args)
}

fn env(name: &str) -> Option<String> {
    std::env::var(name).ok().filter(|v| !v.trim().is_empty())
}

fn state_dir() -> PathBuf {
    env("STATE_DIRECTORY")
        .and_then(|dirs| dirs.split(':').next().map(PathBuf::from))
        .unwrap_or_else(|| PathBuf::from(STATE_DIR))
}

fn library_dirs() -> Vec<String> {
    env("NUXIVA_RUNTIME_PATH")
        .map(|raw| {
            raw.split(':')
                .filter(|dir| dir.starts_with('/') && !dir.split('/').any(|p| p == ".."))
                .take(8)
                .map(str::to_owned)
                .collect()
        })
        .unwrap_or_default()
}

fn descriptors() -> Vec<nuxiva_satellite::backends::Descriptor> {
    let dir = env("NUXIVA_ACCELERATORS_DIR").unwrap_or_else(|| EXTENSIONS_DIR.to_owned());
    let (extensions, rejected) = load_extensions(Path::new(&dir));
    for item in rejected {
        agent::log(&format!("extension_rejected {} {}", item.file, item.reason));
    }
    merge(builtin(), extensions)
}

fn vault(root: &Root) -> Vault {
    Vault::new(state_dir(), root.read_trim("/etc/machine-id").as_deref())
}

fn identity_labels(args: &Args, root: &Root) -> Result<(String, String, String), String> {
    let hostname = root
        .read_trim("/proc/sys/kernel/hostname")
        .unwrap_or_else(|| "satellite".to_owned());
    let name = args
        .name
        .clone()
        .or_else(|| env("NUXIVA_NODE_NAME"))
        .unwrap_or_else(|| hostname.clone());
    let kind = args
        .kind
        .clone()
        .or_else(|| env("NUXIVA_NODE_TYPE"))
        .unwrap_or_else(|| "satellite".to_owned());
    if !service::valid_label(&name) {
        return Err("nome del nodo non valido".into());
    }
    if !NODE_TYPES.contains(&kind.as_str()) {
        return Err(format!(
            "tipo non valido: usa uno tra {}",
            NODE_TYPES.join(", ")
        ));
    }
    Ok((node_id(&hostname, &name), name, kind))
}

fn enroll_from(path: &Path, args: &Args, root: &Root, wipe: bool) -> Result<(), String> {
    let text = std::fs::read_to_string(path).map_err(|e| format!("{}: {e}", path.display()))?;
    let file = EnrollFile::parse(&text, now())?;
    let (id, name, kind) = identity_labels(args, root)?;
    let identity = redeem(&file, &id, &name, &kind).map_err(|e| e.to_string())?;
    vault(root).save(&identity).map_err(|e| e.to_string())?;
    if wipe {
        shred(path).map_err(|e| e.to_string())?;
    }
    agent::log(&format!("enrolled {id}"));
    Ok(())
}

fn probe(args: &Args) -> Result<(), String> {
    let root = Root::new(args.root.clone().unwrap_or_else(|| PathBuf::from("/")));
    let found = profile(&root, &descriptors(), &library_dirs());
    let plan = plan(&found);
    let out = serde_json::json!({"profile": found, "plan": plan});
    println!(
        "{}",
        serde_json::to_string_pretty(&out).map_err(|e| e.to_string())?
    );
    Ok(())
}

fn run(args: &Args) -> Result<(), String> {
    let root = Root::default();
    let vault = vault(&root);
    if !vault.exists() {
        let credential = env("CREDENTIALS_DIRECTORY").map(|dir| PathBuf::from(dir).join("enroll"));
        let path = args
            .file
            .clone()
            .or(credential)
            .ok_or("nodo non iscritto: esegui prima enroll")?;
        enroll_from(&path, args, &root, args.file.is_some())?;
    }
    let identity = vault.load().map_err(|e| e.to_string())?;
    let link = Link::open(&identity, Duration::from_secs(30)).map_err(|e| e.to_string())?;
    let mut runner = Runner::new(root, descriptors(), library_dirs());
    match runner.run(&link).map_err(|e| e.to_string())? {
        Exit::Restart => Ok(()),
        Exit::Revoked => {
            vault.destroy().map_err(|e| e.to_string())?;
            Err("il server ha revocato questo nodo: iscrivilo di nuovo".into())
        }
    }
}

fn install(args: &Args) -> Result<(), String> {
    if !rustix::process::geteuid().is_root() {
        return Err("serve sudo per installare il servizio".into());
    }
    let root = Root::default();
    let file = args.file.as_ref().ok_or("serve --file <iscrizione.json>")?;
    let text = std::fs::read_to_string(file).map_err(|e| format!("{}: {e}", file.display()))?;
    EnrollFile::parse(&text, now())?;
    let (_, name, kind) = identity_labels(args, &root)?;
    let room = args.room.clone().unwrap_or_default();
    let groups = service::existing_groups(
        &root.read("/etc/group").unwrap_or_default(),
        &["audio", "video", "render"],
    );
    let binary = std::env::current_exe().map_err(|e| e.to_string())?;
    let unit = service::unit(&binary, &name, &kind, &room, &groups)?;
    let credential = Path::new(service::ENROLL_CREDENTIAL);
    if let Some(parent) = credential.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    nuxiva_satellite::vault::write_atomic(credential, text.as_bytes())
        .map_err(|e| e.to_string())?;
    nuxiva_satellite::vault::write_atomic(Path::new(service::UNIT_PATH), unit.as_bytes())
        .map_err(|e| e.to_string())?;
    for step in [
        &["daemon-reload"][..],
        &["enable", "--now", "nuxiva-satellite"][..],
    ] {
        let status = Command::new("systemctl")
            .args(step)
            .status()
            .map_err(|e| e.to_string())?;
        if !status.success() {
            return Err(format!("systemctl {} non riuscito", step.join(" ")));
        }
    }
    agent::log("service_installed");
    Ok(())
}

fn main() -> ExitCode {
    let outcome = parse_args().and_then(|args| match args.command.as_str() {
        "probe" => probe(&args),
        "enroll" => {
            let path = args.file.clone().ok_or("serve --file <iscrizione.json>")?;
            enroll_from(&path, &args, &Root::default(), true)
        }
        "run" => run(&args),
        "forget" => vault(&Root::default()).destroy().map_err(|e| e.to_string()),
        "install-service" => install(&args),
        _ => Err(USAGE.into()),
    });
    match outcome {
        Ok(()) => ExitCode::SUCCESS,
        Err(message) => {
            eprintln!("nuxiva-satellite: {message}");
            ExitCode::FAILURE
        }
    }
}
