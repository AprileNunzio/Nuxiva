use std::path::PathBuf;
use std::process::ExitCode;

use agency_codeindex::bench::{BenchConfig, BenchError, run};

fn execute(args: &[String]) -> Result<(), BenchError> {
    let (Some(config_path), Some(root)) = (args.first(), args.get(1)) else {
        return Err(BenchError::Config(
            "usage: codeindex_bench <config.json> <corpus_root> [report.json]",
        ));
    };
    let config = BenchConfig::from_json(&std::fs::read_to_string(config_path)?)?;
    let report = run(&PathBuf::from(root), &config)?;
    let rendered = serde_json::to_string_pretty(&report)?;
    match args.get(2) {
        Some(output) => std::fs::write(output, format!("{rendered}\n"))?,
        None => println!("{rendered}"),
    }
    Ok(())
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    match execute(&args) {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("{error}");
            ExitCode::FAILURE
        }
    }
}
