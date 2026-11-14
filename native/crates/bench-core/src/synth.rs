use crate::barge::BargeTrial;
use crate::latency::StageTimes;
use crate::observations::{Observations, SCHEMA, Source, UtteranceObs};
use crate::scene::{Background, Class};
use crate::speaker::SpeakerTrial;
use crate::wake::WakeTrial;

pub const SENTENCES: [&str; 24] = [
    "accendi la luce del salotto",
    "che tempo farà domani mattina",
    "metti una sveglia alle sette e mezza",
    "spegni tutte le luci della cucina",
    "quanto manca all'arrivo del corriere",
    "leggi i messaggi non letti di oggi",
    "abbassa il volume della musica",
    "apri la lista della spesa",
    "ricordami di chiamare il medico alle cinque",
    "imposta il riscaldamento a ventuno gradi",
    "dimmi cosa c'è in agenda per domani",
    "ferma la riproduzione e riprendi più tardi",
    "avvisa la famiglia che sto arrivando",
    "quanti passi ho fatto oggi",
    "aggiungi il latte alla lista della spesa",
    "chiudi le tapparelle della camera",
    "cerca una ricetta con le zucchine",
    "che ore sono a new york",
    "riassumi le ultime notizie della giornata",
    "prepara il resoconto della settimana",
    "controlla se la porta d'ingresso è chiusa",
    "spegni la televisione tra mezz'ora",
    "dimmi la temperatura della stanza",
    "organizza i documenti da firmare entro venerdì",
];

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Profile {
    Healthy,
    Degraded,
}

#[derive(Debug, Clone, Copy)]
pub struct Scale {
    pub utterances: usize,
    pub wake_positives: usize,
    pub wake_negatives: usize,
    pub speaker: usize,
    pub barge: usize,
}

impl Scale {
    #[must_use]
    pub const fn standard() -> Self {
        Self {
            utterances: 240,
            wake_positives: 100,
            wake_negatives: 720,
            speaker: 800,
            barge: 500,
        }
    }
}

struct Rng(u64);

impl Rng {
    fn next(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.0;
        z = (z ^ z.wrapping_shr(30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ z.wrapping_shr(27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ z.wrapping_shr(31)
    }

    fn unit(&mut self) -> f64 {
        let top = u32::try_from(self.next().wrapping_shr(32)).unwrap_or(u32::MAX);
        f64::from(top) / 4_294_967_296.0
    }

    fn chance(&mut self, p: f64) -> bool {
        self.unit() < p
    }

    fn range(&mut self, lo: f64, hi: f64) -> f64 {
        lo + self.unit() * (hi - lo)
    }

    fn below(&mut self, n: usize) -> usize {
        let n64 = u64::try_from(n.max(1)).unwrap_or(1);
        usize::try_from(self.next().checked_rem(n64).unwrap_or_default()).unwrap_or_default()
    }
}

struct Rates {
    word_error: f64,
    tail: f64,
    stretch: f64,
    wake_miss: f64,
    wake_false: f64,
    speaker_known_miss: f64,
    leak: f64,
    barge_miss: f64,
    barge_false: f64,
}

impl Rates {
    fn of(profile: Profile) -> Self {
        match profile {
            Profile::Healthy => Self {
                word_error: 0.03,
                tail: 0.015,
                stretch: 1.0,
                wake_miss: 0.01,
                wake_false: 0.0005,
                speaker_known_miss: 0.015,
                leak: 0.0008,
                barge_miss: 0.04,
                barge_false: 0.004,
            },
            Profile::Degraded => Self {
                word_error: 0.22,
                tail: 0.10,
                stretch: 2.2,
                wake_miss: 0.22,
                wake_false: 0.012,
                speaker_known_miss: 0.2,
                leak: 0.12,
                barge_miss: 0.35,
                barge_false: 0.12,
            },
        }
    }
}

fn corrupt(rng: &mut Rng, sentence: &str, p: f64) -> String {
    let mut out: Vec<String> = Vec::new();
    for word in sentence.split_whitespace() {
        if !rng.chance(p) {
            out.push(word.to_owned());
            continue;
        }
        match rng.below(3) {
            0 => out.push("zzz".to_owned()),
            1 => {}
            _ => {
                out.push(word.to_owned());
                out.push("zzz".to_owned());
            }
        }
    }
    out.join(" ")
}

fn stages(rng: &mut Rng, r: &Rates) -> StageTimes {
    let tail = if rng.chance(r.tail) { 3.0 } else { 1.0 };
    let k = r.stretch * tail;
    StageTimes {
        listen_ms: rng.range(60.0, 120.0) * k,
        transcribe_ms: rng.range(150.0, 300.0) * k,
        decide_ms: rng.range(40.0, 100.0) * k,
        respond_ms: rng.range(100.0, 250.0) * k,
        tts_ms: rng.range(80.0, 180.0) * k,
    }
}

fn background(rng: &mut Rng) -> Background {
    match rng.below(5) {
        0 => Background::Radio,
        1 => Background::Music,
        2 => Background::Tv,
        _ => Background::None,
    }
}

fn speaker_trial(rng: &mut Rng, r: &Rates) -> SpeakerTrial {
    let truth = match rng.below(20) {
        0..=7 => Class::Known,
        8..=12 => Class::Guest,
        _ => Class::Broadcast,
    };
    let bg = if truth == Class::Broadcast {
        match rng.below(3) {
            0 => Background::Radio,
            1 => Background::Music,
            _ => Background::Tv,
        }
    } else if rng.chance(0.25) {
        background(rng)
    } else {
        Background::None
    };
    let slot = u16::try_from(rng.below(3)).unwrap_or_default();
    let (predicted, predicted_slot, truth_slot) = match truth {
        Class::Known => {
            if rng.chance(r.speaker_known_miss) {
                let wrong = if rng.chance(0.7) {
                    (Class::Guest, None)
                } else {
                    (Class::Known, Some(slot.saturating_add(1)))
                };
                (wrong.0, wrong.1, Some(slot))
            } else {
                (Class::Known, Some(slot), Some(slot))
            }
        }
        Class::Guest | Class::Broadcast => {
            if rng.chance(r.leak) {
                (Class::Known, Some(slot), None)
            } else if truth == Class::Guest {
                (Class::Guest, None, None)
            } else if rng.chance(0.8) {
                (Class::Broadcast, None, None)
            } else {
                (Class::Guest, None, None)
            }
        }
    };
    SpeakerTrial {
        truth,
        predicted,
        truth_slot,
        predicted_slot,
        background: bg,
    }
}

fn barge_trial(rng: &mut Rng, r: &Rates) -> BargeTrial {
    let expect_barge = rng.chance(0.5);
    let bg = background(rng);
    let fired = if expect_barge {
        !rng.chance(r.barge_miss)
    } else {
        rng.chance(r.barge_false)
    };
    let reaction_ms = if fired && expect_barge {
        Some(rng.range(110.0, 280.0) * r.stretch)
    } else if fired {
        Some(rng.range(150.0, 400.0))
    } else {
        None
    };
    BargeTrial {
        expect_barge,
        fired,
        reaction_ms,
        background: bg,
    }
}

#[must_use]
pub fn generate(seed: u64, profile: Profile, scale: Scale) -> Observations {
    let mut rng = Rng(seed);
    let r = Rates::of(profile);
    let mut utterances = Vec::with_capacity(scale.utterances);
    for index in 0..scale.utterances {
        let sentence = SENTENCES
            .get(rng.below(SENTENCES.len()))
            .copied()
            .unwrap_or_default();
        utterances.push(UtteranceObs {
            id: format!("u{index:05}"),
            reference: sentence.to_owned(),
            hypothesis: corrupt(&mut rng, sentence, r.word_error),
            stages: stages(&mut rng, &r),
        });
    }
    let mut wake = Vec::new();
    for _ in 0..scale.wake_positives {
        wake.push(WakeTrial {
            expect_wake: true,
            fired: !rng.chance(r.wake_miss),
            audio_ms: 4_000,
            background: background(&mut rng),
        });
    }
    for _ in 0..scale.wake_negatives {
        let bg = background(&mut rng);
        let boost = if bg.is_noisy() { 2.0 } else { 1.0 };
        wake.push(WakeTrial {
            expect_wake: false,
            fired: rng.chance(r.wake_false * boost),
            audio_ms: 30_000,
            background: bg,
        });
    }
    let speaker = (0..scale.speaker)
        .map(|_| speaker_trial(&mut rng, &r))
        .collect();
    let barge = (0..scale.barge)
        .map(|_| barge_trial(&mut rng, &r))
        .collect();
    Observations {
        schema: SCHEMA,
        source: Source::Synthetic,
        corpus: format!("synthetic-{seed}"),
        utterances,
        wake,
        speaker,
        barge,
    }
}
