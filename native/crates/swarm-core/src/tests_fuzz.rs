use crate::settings::Settings;
use crate::wire::{Percept, Plan, StepEvent, TaskEnvelope, WorkerError, WorkerResult, decode};

const SEEDS: [&str; 5] = [
    r#"{"schema_version":1,"id":"p1","at_ms":5,"channel":"voice","text":"ciao","speaker":"anna","presence":["anna"],"emotion":{"valence":-200,"arousal":300,"source":"voce","at_ms":4}}"#,
    r#"{"schema_version":1,"id":"plan.one","steps":[{"id":"a","worker_template":"cuoco","intent":"ricette","goal_ref":"g","needs_graph":true,"budget":{"tokens":10,"tool_calls":2,"time_ms":50},"verify":"judge"}],"edges":[{"from":"a","to":"a"}]}"#,
    r#"{"schema_version":1,"id":"t1","intent":"ricette","input":"p1","constraints":{"risk_max":2,"deadline_ms":5000,"tokens_max":1000,"tool_calls_max":4,"level":"standard"},"depth":1}"#,
    r#"{"schema_version":1,"task":"t","step":"a","outcome":"done","output":{"k":[1,2,{"x":null}]},"evidence":["e1"],"usage":{"tokens":1,"tool_calls":1,"time_ms":1}}"#,
    r#"{"schema_version":1,"task":"t","step":"a","phase":"started","at_ms":3}"#,
];

struct Rng(u64);

impl Rng {
    fn next(&mut self) -> u64 {
        self.0 ^= self.0 << 13;
        self.0 ^= self.0 >> 7;
        self.0 ^= self.0 << 17;
        self.0
    }

    fn below(&mut self, bound: usize) -> usize {
        let bound = u64::try_from(bound.max(1)).unwrap_or(1);
        usize::try_from(self.next().checked_rem(bound).unwrap_or(0)).unwrap_or(0)
    }
}

fn mutate(seed: &[u8], rng: &mut Rng) -> Vec<u8> {
    let mut data = seed.to_vec();
    for _ in 0..=rng.below(4) {
        let at = rng.below(data.len());
        match rng.below(5) {
            0 => {
                if let Some(byte) = data.get_mut(at) {
                    *byte ^= 1 << rng.below(8);
                }
            }
            1 => {
                if at < data.len() {
                    data.remove(at);
                }
            }
            2 => data.insert(at, u8::try_from(rng.below(256)).unwrap_or(0)),
            3 => data.truncate(at),
            _ => {
                let end = at.saturating_add(rng.below(24)).min(data.len());
                let chunk: Vec<u8> = data.get(at..end).map(<[u8]>::to_vec).unwrap_or_default();
                data.splice(at..at, chunk);
            }
        }
        if data.is_empty() {
            data.push(b'{');
        }
    }
    data
}

#[test]
fn mutated_payloads_never_panic() {
    let settings = Settings::default();
    let mut rng = Rng(0x9E37_79B9_7F4A_7C15);
    let mut accepted = 0_usize;
    for seed in SEEDS {
        for _ in 0..40_000 {
            let input = mutate(seed.as_bytes(), &mut rng);
            accepted += usize::from(decode::<Percept>(&input, &settings).is_ok());
            accepted += usize::from(decode::<Plan>(&input, &settings).is_ok());
            accepted += usize::from(decode::<TaskEnvelope>(&input, &settings).is_ok());
            accepted += usize::from(decode::<WorkerResult>(&input, &settings).is_ok());
            accepted += usize::from(decode::<WorkerError>(&input, &settings).is_ok());
            accepted += usize::from(decode::<StepEvent>(&input, &settings).is_ok());
        }
    }
    assert!(accepted > 0);
}

#[test]
fn deeply_nested_input_is_rejected_not_crashed() {
    let settings = Settings::default();
    let deep = format!("{}1{}", "[".repeat(100_000), "]".repeat(100_000));
    let wrapped =
        format!(r#"{{"schema_version":1,"task":"t","step":"a","outcome":"done","output":{deep}}}"#);
    assert!(decode::<WorkerResult>(wrapped.as_bytes(), &settings).is_err());
}
