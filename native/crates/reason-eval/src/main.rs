use std::path::Path;
use std::process::ExitCode;

use reason_eval::{EvalError, EvalResult, Gates, Report, compare};

fn arg(args: &[String], index: usize) -> EvalResult<&str> {
    args.get(index)
        .map(String::as_str)
        .ok_or(EvalError::Invalid("usage"))
}

fn load_report(path: &str) -> EvalResult<Report> {
    Ok(serde_json::from_slice(&bench_core::read_limited(
        Path::new(path),
    )?)?)
}

fn run(args: &[String]) -> EvalResult<(String, bool)> {
    let command = arg(args, 1)?;
    if command == "compare" {
        let comparison = compare(
            &load_report(arg(args, 2)?)?,
            &load_report(arg(args, 3)?)?,
            &Gates::default(),
        )?;
        let passed = comparison.regressions.is_empty();
        return Ok((serde_json::to_string_pretty(&comparison)?, passed));
    }
    let cases = reason_eval::expand(&reason_eval::load_dir(Path::new(arg(args, 2)?))?)?;
    reason_eval::enforce_floor(&cases)?;
    match command {
        "validate" => Ok((
            serde_json::to_string(&serde_json::json!({
                "cases": cases.len(),
                "dataset": reason_eval::fingerprint(&cases),
            }))?,
            true,
        )),
        "score" => {
            let bytes = bench_core::read_limited(Path::new(arg(args, 3)?))?;
            let report = reason_eval::build(&cases, &reason_eval::parse_outcomes(&bytes)?)?;
            Ok((serde_json::to_string_pretty(&report)?, true))
        }
        _ => Err(EvalError::Invalid("usage")),
    }
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().collect();
    match run(&args) {
        Ok((output, passed)) => {
            println!("{output}");
            if passed {
                ExitCode::SUCCESS
            } else {
                ExitCode::from(2)
            }
        }
        Err(error) => {
            eprintln!("{error}");
            ExitCode::FAILURE
        }
    }
}
