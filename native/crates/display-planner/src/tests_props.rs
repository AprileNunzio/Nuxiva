use crate::candidate::{Candidate, Size};
use crate::context::{Mode, Previous};
use crate::nucleus::Form;
use crate::plan::{Input, plan};
use crate::policy::PlannerPolicy;
use crate::tests::{cand, ctx, screen};
use nuxiva_display_domain::{AudienceKind, Sensitivity};

struct Rng(u64);

impl Rng {
    fn next(&mut self) -> u64 {
        self.0 ^= self.0 << 13;
        self.0 ^= self.0 >> 7;
        self.0 ^= self.0 << 17;
        self.0
    }

    fn below(&mut self, n: u64) -> u64 {
        self.next().checked_rem(n).unwrap_or(0)
    }

    fn pick<T: Copy>(&mut self, items: &[T]) -> T {
        let len = u64::try_from(items.len()).unwrap_or(1).max(1);
        let index = usize::try_from(self.below(len)).unwrap_or(0);
        items.get(index).copied().unwrap_or_else(|| unreachable!())
    }
}

const WIDGETS: [&str; 8] = [
    "weather",
    "music",
    "health_hub",
    "code_view",
    "alarm",
    "tv_player",
    "clock",
    "system_monitor",
];
const SIZES: [Size; 5] = [Size::S, Size::M, Size::L, Size::Xl, Size::Full];
const LEVELS: [Sensitivity; 4] = [
    Sensitivity::Public,
    Sensitivity::Household,
    Sensitivity::Personal,
    Sensitivity::Sensitive,
];
const KINDS: [AudienceKind; 5] = [
    AudienceKind::Empty,
    AudienceKind::GuestOnly,
    AudienceKind::Mixed,
    AudienceKind::Authorized,
    AudienceKind::Uncertain,
];
const MODES: [Mode; 3] = [Mode::Conversation, Mode::Project, Mode::Ambient];

fn random(rng: &mut Rng, i: usize) -> Candidate {
    let mut c = cand(&format!("k{i}"), rng.pick(&WIDGETS));
    let any = rng.pick(&SIZES);
    c.size = rng.pick(&[Size::S, Size::M, Size::L, Size::Xl, Size::S, Size::M, any]);
    c.sensitivity = rng.pick(&LEVELS);
    c.owner = rng
        .pick(&[None, Some("nunzio"), Some("anna")])
        .map(str::to_owned);
    c.importance = u8::try_from(rng.below(101)).unwrap_or(0);
    c.urgency = u8::try_from(rng.below(4)).unwrap_or(0);
    c.cost = rng.pick(&[0.5, 1.0, 2.0, 4.0]);
    c.forced = rng.below(9) == 0;
    c.exclusive = rng.pick(&[None, None, Some("video")]).map(str::to_owned);
    c
}

#[test]
fn random_plans_respect_every_invariant() {
    let mut rng = Rng(0x9e37_79b9_7f4a_7c15);
    let policy = PlannerPolicy::default();
    for round in 0..600 {
        let count = usize::try_from(rng.below(24)).unwrap_or(0);
        let candidates: Vec<Candidate> = (0..count).map(|i| random(&mut rng, i)).collect();
        let mut context = ctx(rng.pick(&KINDS), rng.pick(&MODES));
        context.alone = rng.below(2) == 0;
        let input = Input {
            screen: screen(),
            context: context.clone(),
            candidates,
            previous: Previous::default(),
            now_ms: 0,
        };
        let Ok(p) = plan(&input, &policy) else {
            unreachable!("round {round}")
        };
        assert_eq!(
            Ok(&p),
            plan(&input, &policy).as_ref(),
            "determinismo {round}"
        );
        let mut optional = (0_u8, 0.0_f32);
        for s in &p.shown {
            let Some(c) = input.candidates.iter().find(|c| c.key == s.key) else {
                unreachable!()
            };
            if matches!(
                c.sensitivity,
                Sensitivity::Personal | Sensitivity::Sensitive
            ) {
                assert_eq!(
                    context.audience,
                    AudienceKind::Authorized,
                    "privacy {round}"
                );
                assert!(
                    c.owner.as_ref().is_none_or(|o| context.present.contains(o)),
                    "owner {round}"
                );
            }
            if !c.must_show() {
                optional = (optional.0.saturating_add(1), optional.1 + c.cost);
            }
            if let (Some(slot), Some(core)) = (s.slot, p.nucleus.slot)
                && p.nucleus.form != Form::WhisperPill
            {
                assert!(!slot.overlaps(core), "nucleo coperto {round}");
            }
        }
        assert!(optional.0 <= p.cap, "tetto {round}");
        assert!(optional.1 <= screen().budget, "budget {round}");
        let slots: Vec<_> = p.shown.iter().filter_map(|s| s.slot).collect();
        for (i, a) in slots.iter().enumerate() {
            assert!(
                a.col.saturating_add(a.w) <= 12 && a.row.saturating_add(a.h) <= p.rows,
                "fuori griglia {round}"
            );
            for b in slots.iter().skip(i.saturating_add(1)) {
                assert!(!a.overlaps(*b), "sovrapposizione {round}");
            }
        }
    }
}
