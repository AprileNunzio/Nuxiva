use crate::model::{Case, Outcome};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Verdict {
    pub intent_match: bool,
    pub success: bool,
    pub wrong_action: bool,
}

#[must_use]
pub fn judge(case: &Case, outcome: &Outcome) -> Verdict {
    let intent_match = case.expected.intent == outcome.intent;
    let wrong_action = outcome
        .effects
        .iter()
        .any(|effect| !case.expected.effects.contains(effect));
    let covered = case.expected.effects.is_subset(&outcome.effects);
    Verdict {
        intent_match,
        success: intent_match && covered && outcome.completed && !wrong_action,
        wrong_action,
    }
}
