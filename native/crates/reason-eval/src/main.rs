use std::path::Path;
use std::process::ExitCode;

fn run(args: &[String]) -> reason_eval::EvalResult<String> {
    let dir = args
        .get(2)
        .ok_or(reason_eval::EvalError::Invalid("usage"))?;
    let cases = reason_eval::expand(&reason_eval::load_dir(Path::new(dir))?)?;
    reason_eval::enforce_floor(&cases)?;
    match args.get(1).map(String::as_str) {
        Some("validate") => Ok(serde_json::to_string(&serde_json::json!({
            "cases": cases.len(),
        }))?),
        Some("score") => {
            let path = args
                .get(3)
                .ok_or(reason_eval::EvalError::Invalid("usage"))?;
            let bytes = bench_core::read_limited(Path::new(path))?;
            let report = reason_eval::build(&cases, &reason_eval::parse_outcomes(&bytes)?)?;
            Ok(serde_json::to_string_pretty(&report)?)
        }
        _ => Err(reason_eval::EvalError::Invalid("usage")),
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
