use std::collections::BTreeMap;
use std::path::Path;

use nuxiva_collaudo_core::Verdict;
use serde::Serialize;

use crate::error::{BenchError, BenchResult};
use crate::fsio::{read_limited, write_atomic};
use crate::ledger::{Criteria, Kind, Ledger};
use crate::observations::{Observations, SCHEMA};
use crate::report::{BenchReport, compare, run};
use crate::synth::{Profile, SENTENCES, Scale, generate};
use crate::thresholds::Thresholds;

pub const EXIT_PASS: i32 = 0;
pub const EXIT_WARN: i32 = 1;
pub const EXIT_FAIL: i32 = 2;
pub const EXIT_INSUFFICIENT: i32 = 3;

#[derive(Debug)]
pub struct Outcome {
    pub stdout: String,
    pub code: i32,
}

#[must_use]
pub fn verdict_code(verdict: Verdict) -> i32 {
    match verdict {
        Verdict::Pass => EXIT_PASS,
        Verdict::Warn => EXIT_WARN,
        Verdict::Fail => EXIT_FAIL,
        Verdict::Insufficient => EXIT_INSUFFICIENT,
    }
}

struct Flags(BTreeMap<String, String>);

impl Flags {
    fn parse(args: &[String], allowed: &[&str]) -> BenchResult<Self> {
        let mut map = BTreeMap::new();
        let mut iter = args.iter();
        while let Some(arg) = iter.next() {
            let key = arg.strip_prefix("--").ok_or(BenchError::Invalid("flag"))?;
            if !allowed.contains(&key) {
                return Err(BenchError::Invalid("flag_unknown"));
            }
            let value = iter.next().ok_or(BenchError::Invalid("flag_value"))?;
            if map.insert(key.to_owned(), value.clone()).is_some() {
                return Err(BenchError::Invalid("flag_duplicate"));
            }
        }
        Ok(Self(map))
    }

    fn get(&self, key: &str) -> Option<&str> {
        self.0.get(key).map(String::as_str)
    }

    fn need(&self, key: &str) -> BenchResult<&str> {
        self.get(key).ok_or(BenchError::Invalid("flag_missing"))
    }

    fn number<T: std::str::FromStr>(&self, key: &str) -> BenchResult<Option<T>> {
        self.get(key)
            .map(|v| {
                v.parse::<T>()
                    .map_err(|_| BenchError::Invalid("flag_number"))
            })
            .transpose()
    }
}

fn json<T: Serialize>(value: &T) -> BenchResult<String> {
    Ok(serde_json::to_string(value)?)
}

fn emit(flags: &Flags, text: String) -> BenchResult<String> {
    match flags.get("out") {
        Some(path) => {
            write_atomic(Path::new(path), text.as_bytes())?;
            Ok(String::new())
        }
        None => Ok(text),
    }
}

fn synth(args: &[String]) -> BenchResult<Outcome> {
    let flags = Flags::parse(args, &["seed", "profile", "out"])?;
    let seed = flags.number::<u64>("seed")?.unwrap_or(1);
    let profile = match flags.get("profile").unwrap_or("healthy") {
        "healthy" => Profile::Healthy,
        "degraded" => Profile::Degraded,
        _ => return Err(BenchError::Invalid("profile")),
    };
    let obs = generate(seed, profile, Scale::standard());
    Ok(Outcome {
        stdout: emit(&flags, json(&obs)?)?,
        code: EXIT_PASS,
    })
}

fn bench(args: &[String]) -> BenchResult<Outcome> {
    let flags = Flags::parse(args, &["obs", "thresholds", "baseline", "out"])?;
    let obs = Observations::parse(&read_limited(Path::new(flags.need("obs")?))?)?;
    let th = match flags.get("thresholds") {
        Some(path) => Thresholds::parse(&read_limited(Path::new(path))?)?,
        None => Thresholds::default(),
    };
    let mut report = run(&obs, &th)?;
    if let Some(path) = flags.get("baseline") {
        let base: BenchReport = serde_json::from_slice(&read_limited(Path::new(path))?)?;
        if base.schema != SCHEMA {
            return Err(BenchError::Invalid("baseline_schema"));
        }
        compare(&base, &mut report, &th);
    }
    let code = verdict_code(report.verdict);
    Ok(Outcome {
        stdout: emit(&flags, json(&report)?)?,
        code,
    })
}

#[derive(Serialize)]
struct Manifest {
    schema: u32,
    corpus_sentences: Vec<ManifestSentence>,
    minimums: Minimums,
    stages: [&'static str; 5],
}

#[derive(Serialize)]
struct ManifestSentence {
    id: String,
    text: &'static str,
}

#[derive(Serialize)]
struct Minimums {
    utterances: u64,
    wake_positives: u64,
    wake_negative_hours: f64,
    speaker_trials: u64,
    barge_trials: u64,
}

fn manifest(args: &[String]) -> BenchResult<Outcome> {
    let flags = Flags::parse(args, &["out"])?;
    let th = Thresholds::default();
    let doc = Manifest {
        schema: SCHEMA,
        corpus_sentences: SENTENCES
            .iter()
            .enumerate()
            .map(|(i, text)| ManifestSentence {
                id: format!("r{i:04}"),
                text,
            })
            .collect(),
        minimums: Minimums {
            utterances: th.min_utterances,
            wake_positives: th.min_wake_positives,
            wake_negative_hours: th.min_wake_negative_hours,
            speaker_trials: th.min_speaker_trials,
            barge_trials: th.min_barge_trials,
        },
        stages: crate::latency::STAGES,
    };
    Ok(Outcome {
        stdout: emit(&flags, json(&doc)?)?,
        code: EXIT_PASS,
    })
}

fn defaults(args: &[String]) -> BenchResult<Outcome> {
    let flags = Flags::parse(args, &["out"])?;
    Ok(Outcome {
        stdout: emit(&flags, json(&Thresholds::default())?)?,
        code: EXIT_PASS,
    })
}

fn load_ledger(path: &Path) -> BenchResult<Ledger> {
    match read_limited(path) {
        Ok(bytes) => Ledger::parse(&bytes),
        Err(BenchError::Io(e)) if e.kind() == std::io::ErrorKind::NotFound => Ok(Ledger::default()),
        Err(e) => Err(e),
    }
}

fn a12(args: &[String], today: u32) -> BenchResult<Outcome> {
    let (action, rest) = args
        .split_first()
        .ok_or(BenchError::Invalid("a12_action"))?;
    let flags = Flags::parse(rest, &["ledger", "kind", "id", "day"])?;
    let path = Path::new(flags.need("ledger")?);
    let mut ledger = load_ledger(path)?;
    let day = flags.number::<u32>("day")?.unwrap_or(today);
    match action.as_str() {
        "add" => {
            let kind = Kind::parse(flags.need("kind")?)?;
            let added = ledger.append(kind, flags.need("id")?, day)?;
            if added {
                write_atomic(path, json(&ledger)?.as_bytes())?;
            }
            Ok(Outcome {
                stdout: format!("{{\"added\":{added}}}"),
                code: EXIT_PASS,
            })
        }
        "status" => {
            let status = ledger.status(&Criteria::default(), day);
            let code = if status.ready {
                EXIT_PASS
            } else {
                EXIT_INSUFFICIENT
            };
            Ok(Outcome {
                stdout: json(&status)?,
                code,
            })
        }
        _ => Err(BenchError::Invalid("a12_action")),
    }
}

pub fn execute(args: &[String], today: u32) -> BenchResult<Outcome> {
    let (command, rest) = args.split_first().ok_or(BenchError::Invalid("command"))?;
    match command.as_str() {
        "synth" => synth(rest),
        "run" => bench(rest),
        "manifest" => manifest(rest),
        "thresholds" => defaults(rest),
        "a12" => a12(rest, today),
        _ => Err(BenchError::Invalid("command")),
    }
}
