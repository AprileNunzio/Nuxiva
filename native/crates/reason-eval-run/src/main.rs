use std::io::Write;
use std::path::Path;
use std::process::ExitCode;
use std::time::{Duration, Instant};

use nuxiva_llm_client::LlmClient;
use reason_eval_run::{Backend, to_outcome};

const KEY_VARIABLE: &str = "NUXIVA_EVAL_KEY";

async fn run(args: &[String]) -> Result<usize, String> {
    let [_, dir, backend, base, model, out, rest @ ..] = args else {
        return Err(
            "usage: <golden_dir> <ollama|openai> <base_url> <model> <out.jsonl> [limit]".into(),
        );
    };
    let backend = Backend::parse(backend).ok_or("backend")?;
    let limit = rest
        .first()
        .map(|v| v.parse::<usize>().map_err(|_| "limit"))
        .transpose()?
        .unwrap_or(usize::MAX);
    let cases =
        reason_eval::expand(&reason_eval::load_dir(Path::new(dir)).map_err(|e| e.to_string())?)
            .map_err(|e| e.to_string())?;
    reason_eval::enforce_floor(&cases).map_err(|e| e.to_string())?;
    let client = LlmClient::new(base, Duration::from_secs(120), Duration::from_secs(10))
        .map_err(|e| e.to_string())?;
    let key = std::env::var(KEY_VARIABLE).ok().filter(|k| !k.is_empty());
    let mut file = std::fs::File::create(out).map_err(|e| e.to_string())?;
    let mut written = 0usize;
    for case in cases.iter().take(limit) {
        let request = reason_understand::build(&case.text, case.external_content.as_deref());
        let body = backend.body(model, &request);
        let started = Instant::now();
        let reply = client
            .post_json(backend.path(), &body, key.as_deref())
            .await
            .ok()
            .filter(|r| r.status == 200);
        let latency = u64::try_from(started.elapsed().as_millis()).unwrap_or(u64::MAX);
        let extracted = reply.and_then(|r| backend.extract(&r.body));
        let (content, tokens) = extracted.map_or((None, 0), |(c, t)| (Some(c), t));
        let outcome = to_outcome(case, content.as_deref(), tokens, latency);
        let line = serde_json::to_string(&outcome).map_err(|e| e.to_string())?;
        writeln!(file, "{line}").map_err(|e| e.to_string())?;
        written = written.saturating_add(1);
    }
    Ok(written)
}

#[tokio::main]
async fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().collect();
    match run(&args).await {
        Ok(count) => {
            println!("{count}");
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("{error}");
            ExitCode::FAILURE
        }
    }
}
