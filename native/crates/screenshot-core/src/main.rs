use std::path::{Path, PathBuf};
use std::process::ExitCode;

use nuxiva_screenshot::config::Config;
use nuxiva_screenshot::daemon::{Daemon, Format, load_config};
use nuxiva_screenshot::evdev::discover;
use nuxiva_screenshot::session::discover as discover_session;
use nuxiva_screenshot::sink::build;

const DEFAULT_ENV: &str = "/etc/nuxiva/nuxiva.env";
const USAGE: &str =
    "uso: nuxiva-screenshot run|check|now [--env FILE | --config FILE] [--default-target DIR]";

struct Options {
    path: PathBuf,
    format: Format,
    default_target: Option<PathBuf>,
}

fn options(args: &[String]) -> Result<Options, String> {
    let mut out = Options {
        path: PathBuf::from(DEFAULT_ENV),
        format: Format::Env,
        default_target: None,
    };
    let mut iter = args.iter();
    while let Some(flag) = iter.next() {
        let value = iter.next().ok_or_else(|| USAGE.to_owned())?;
        match flag.as_str() {
            "--env" => {
                out.path = PathBuf::from(value);
                out.format = Format::Env;
            }
            "--config" => {
                out.path = PathBuf::from(value);
                out.format = Format::Json;
            }
            "--default-target" => out.default_target = Some(PathBuf::from(value)),
            _ => return Err(USAGE.to_owned()),
        }
    }
    Ok(out)
}

fn check(config: &Config) {
    let devices = discover(Path::new("/sys/class/input"), Path::new("/dev/input"));
    let session = discover_session();
    let report = serde_json::json!({
        "enabled": config.enabled,
        "target_ready": build(config).is_some(),
        "key_devices": devices.len(),
        "session": session.as_ref().map(|s| serde_json::json!({
            "uid": s.uid,
            "locked": s.locked,
            "kind": format!("{:?}", s.kind),
        })),
    });
    println!("{report}");
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let Some((command, rest)) = args.split_first() else {
        eprintln!("{USAGE}");
        return ExitCode::FAILURE;
    };
    let opts = match options(rest) {
        Ok(opts) => opts,
        Err(message) => {
            eprintln!("{message}");
            return ExitCode::FAILURE;
        }
    };
    match command.as_str() {
        "run" => Daemon::new(opts.path, opts.format, opts.default_target).run(),
        "check" => {
            check(&load_config(
                &opts.path,
                opts.format,
                opts.default_target.as_deref(),
            ));
            ExitCode::SUCCESS
        }
        "now" => {
            let mut daemon = Daemon::new(opts.path, opts.format, opts.default_target);
            daemon.reload();
            let session = discover_session();
            let outcome = daemon.handle_trigger(session.as_ref(), std::time::Instant::now());
            println!("{outcome:?}");
            ExitCode::SUCCESS
        }
        _ => {
            eprintln!("{USAGE}");
            ExitCode::FAILURE
        }
    }
}
