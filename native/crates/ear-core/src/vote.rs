pub const MAX_HYPOTHESES: usize = 8;
pub const MAX_WORDS: usize = 256;

#[derive(Debug, Clone, PartialEq)]
pub struct Ballot {
    pub text: String,
    pub agreement: f32,
    pub changed: usize,
}

#[derive(Debug, Clone)]
struct Word {
    surface: String,
    key: String,
}

fn key(word: &str) -> String {
    word.chars()
        .filter(|c| c.is_alphanumeric() || *c == '\'')
        .flat_map(char::to_lowercase)
        .collect()
}

fn words(text: &str) -> Vec<Word> {
    text.split_whitespace()
        .map(|w| Word {
            surface: w.to_owned(),
            key: key(w),
        })
        .filter(|w| !w.key.is_empty())
        .take(MAX_WORDS)
        .collect()
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Step {
    Match(usize, usize),
    Delete(usize),
    Insert(usize),
}

fn align(pivot: &[Word], other: &[Word]) -> Vec<Step> {
    let rows = pivot.len().saturating_add(1);
    let cols = other.len().saturating_add(1);
    let mut cost = vec![0_u32; rows.saturating_mul(cols)];
    let at = |i: usize, j: usize| i.saturating_mul(cols).saturating_add(j);
    for i in 0..rows {
        if let Some(c) = cost.get_mut(at(i, 0)) {
            *c = u32::try_from(i).unwrap_or(u32::MAX);
        }
    }
    for j in 0..cols {
        if let Some(c) = cost.get_mut(at(0, j)) {
            *c = u32::try_from(j).unwrap_or(u32::MAX);
        }
    }
    for (i, p) in pivot.iter().enumerate() {
        for (j, o) in other.iter().enumerate() {
            let (i1, j1) = (i.saturating_add(1), j.saturating_add(1));
            let sub = cost
                .get(at(i, j))
                .copied()
                .unwrap_or(u32::MAX)
                .saturating_add(u32::from(p.key != o.key));
            let del = cost
                .get(at(i, j1))
                .copied()
                .unwrap_or(u32::MAX)
                .saturating_add(1);
            let ins = cost
                .get(at(i1, j))
                .copied()
                .unwrap_or(u32::MAX)
                .saturating_add(1);
            if let Some(c) = cost.get_mut(at(i1, j1)) {
                *c = sub.min(del).min(ins);
            }
        }
    }
    let (mut i, mut j) = (pivot.len(), other.len());
    let mut steps = Vec::new();
    while i > 0 || j > 0 {
        let here = cost.get(at(i, j)).copied().unwrap_or(0);
        let (pi, pj) = (i.saturating_sub(1), j.saturating_sub(1));
        if i > 0 && j > 0 {
            let same = pivot.get(pi).map(|w| &w.key) == other.get(pj).map(|w| &w.key);
            let diag = cost.get(at(pi, pj)).copied().unwrap_or(u32::MAX);
            if diag.saturating_add(u32::from(!same)) == here {
                steps.push(Step::Match(pi, pj));
                i = pi;
                j = pj;
                continue;
            }
        }
        if i > 0
            && cost
                .get(at(pi, j))
                .copied()
                .unwrap_or(u32::MAX)
                .saturating_add(1)
                == here
        {
            steps.push(Step::Delete(pi));
            i = pi;
        } else {
            steps.push(Step::Insert(pj));
            j = pj;
        }
    }
    steps.reverse();
    steps
}

#[derive(Debug, Default, Clone)]
struct Slot {
    options: Vec<(Word, f32)>,
    empty: f32,
}

impl Slot {
    fn add(&mut self, word: &Word, weight: f32) {
        if let Some(entry) = self.options.iter_mut().find(|(w, _)| w.key == word.key) {
            entry.1 += weight;
        } else {
            self.options.push((word.clone(), weight));
        }
    }

    fn winner(&self) -> (Option<&Word>, f32) {
        let best = self.options.iter().min_by(|a, b| b.1.total_cmp(&a.1));
        match best {
            Some((word, weight)) if *weight > self.empty => (Some(word), *weight),
            _ => (None, self.empty),
        }
    }

    fn total(&self) -> f32 {
        self.options.iter().map(|(_, w)| *w).sum::<f32>() + self.empty
    }
}

#[must_use]
pub fn vote(hypotheses: &[(String, f32)]) -> Ballot {
    let ballots: Vec<(Vec<Word>, f32)> = hypotheses
        .iter()
        .take(MAX_HYPOTHESES)
        .map(|(t, w)| {
            (
                words(t),
                if w.is_finite() {
                    w.clamp(0.0, 10.0)
                } else {
                    0.0
                },
            )
        })
        .filter(|(_, w)| *w > 0.0)
        .collect();
    let Some(pivot_index) = ballots
        .iter()
        .enumerate()
        .filter(|(_, (ws, _))| !ws.is_empty())
        .min_by(|a, b| (b.1).1.total_cmp(&(a.1).1))
        .map(|(i, _)| i)
    else {
        return Ballot {
            text: String::new(),
            agreement: 0.0,
            changed: 0,
        };
    };
    let Some((pivot, pivot_weight)) = ballots.get(pivot_index) else {
        return Ballot {
            text: String::new(),
            agreement: 0.0,
            changed: 0,
        };
    };
    let pivot_weight = *pivot_weight;
    let (slots, gaps) = fill(pivot, pivot_weight, pivot_index, &ballots);
    assemble(pivot, &slots, &gaps)
}

fn fill(
    pivot: &[Word],
    pivot_weight: f32,
    pivot_index: usize,
    ballots: &[(Vec<Word>, f32)],
) -> (Vec<Slot>, Vec<Slot>) {
    let mut slots: Vec<Slot> = pivot
        .iter()
        .map(|w| {
            let mut s = Slot::default();
            s.add(w, pivot_weight);
            s
        })
        .collect();
    let mut gaps: Vec<Slot> = vec![Slot::default(); pivot.len().saturating_add(1)];
    for (index, (other, weight)) in ballots.iter().enumerate() {
        if index == pivot_index {
            continue;
        }
        let mut gap_index = 0_usize;
        let mut filled = vec![false; gaps.len()];
        for step in align(pivot, other) {
            match step {
                Step::Match(i, j) => {
                    if let (Some(slot), Some(word)) = (slots.get_mut(i), other.get(j)) {
                        slot.add(word, *weight);
                    }
                    gap_index = i.saturating_add(1);
                }
                Step::Delete(i) => {
                    if let Some(slot) = slots.get_mut(i) {
                        slot.empty += weight;
                    }
                    gap_index = i.saturating_add(1);
                }
                Step::Insert(j) => {
                    if let (Some(gap), Some(word)) = (gaps.get_mut(gap_index), other.get(j)) {
                        gap.add(word, *weight);
                        if let Some(f) = filled.get_mut(gap_index) {
                            *f = true;
                        }
                    }
                }
            }
        }
        for (gap, was) in gaps.iter_mut().zip(filled) {
            if !was {
                gap.empty += weight;
            }
        }
    }
    for gap in &mut gaps {
        gap.empty += pivot_weight;
    }
    (slots, gaps)
}

fn assemble(pivot: &[Word], slots: &[Slot], gaps: &[Slot]) -> Ballot {
    let mut out: Vec<String> = Vec::new();
    let mut agreement = 0.0_f32;
    let mut columns = 0_u32;
    let mut changed = 0_usize;
    for (index, gap) in gaps.iter().enumerate() {
        if let (Some(word), _) = gap.winner() {
            out.push(word.surface.clone());
            changed = changed.saturating_add(1);
        }
        if let Some(slot) = slots.get(index) {
            let (word, weight) = slot.winner();
            let total = slot.total();
            if total > 0.0 {
                agreement += weight / total;
                columns = columns.saturating_add(1);
            }
            match word {
                Some(w) => {
                    if pivot.get(index).map(|p| &p.key) != Some(&w.key) {
                        changed = changed.saturating_add(1);
                    }
                    out.push(w.surface.clone());
                }
                None => changed = changed.saturating_add(1),
            }
        }
    }
    #[allow(clippy::cast_precision_loss)]
    let agreement = if columns == 0 {
        0.0
    } else {
        agreement / columns as f32
    };
    Ballot {
        text: out.join(" "),
        agreement,
        changed,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn ballot(items: &[(&str, f32)]) -> Ballot {
        let owned: Vec<(String, f32)> = items.iter().map(|(t, w)| ((*t).to_owned(), *w)).collect();
        vote(&owned)
    }

    #[test]
    fn the_majority_fixes_a_misheard_word() {
        let out = ballot(&[
            ("Jarvis e tempo fa domani", 1.5),
            ("Jarvis che tempo fa domani", 1.0),
            ("Jarvis che tempo fa domani?", 1.0),
        ]);
        assert_eq!(out.text, "Jarvis che tempo fa domani");
        assert_eq!(out.changed, 1);
        assert!(out.agreement > 0.7 && out.agreement < 1.0);
    }

    #[test]
    fn a_word_lost_by_one_microphone_comes_back_from_the_others() {
        let out = ballot(&[
            ("tempo fa domani", 1.5),
            ("che tempo fa domani", 1.0),
            ("che tempo fa domani", 1.0),
        ]);
        assert_eq!(out.text, "che tempo fa domani");
    }

    #[test]
    fn a_lone_extra_word_is_dropped_and_agreement_is_full_when_all_agree() {
        let out = ballot(&[
            ("accendi la luce", 1.5),
            ("accendi la luce grazie", 1.0),
            ("accendi la luce", 1.0),
        ]);
        assert_eq!(out.text, "accendi la luce");
        let same = ballot(&[("accendi la luce", 1.0), ("Accendi la luce.", 1.0)]);
        assert!((same.agreement - 1.0).abs() < 1e-6);
        assert_eq!(same.changed, 0);
    }

    #[test]
    fn the_strongest_single_hypothesis_wins_ties_and_empty_input_is_safe() {
        assert_eq!(ballot(&[("spegni", 2.0), ("spengo", 1.0)]).text, "spegni");
        assert_eq!(ballot(&[]).text, "");
        assert_eq!(ballot(&[("", 1.0), ("ciao", f32::NAN)]).text, "");
    }
}
