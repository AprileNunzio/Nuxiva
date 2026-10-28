use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct Literal(pub i32);

impl Literal {
    #[must_use]
    pub const fn var(self) -> usize {
        self.0.unsigned_abs() as usize
    }

    #[must_use]
    pub const fn is_positive(self) -> bool {
        self.0 > 0
    }

    #[must_use]
    pub const fn negate(self) -> Self {
        Self(self.0.wrapping_neg())
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Clause {
    pub literals: Vec<Literal>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SatResult {
    Satisfiable,
    Unsatisfiable,
}

#[derive(Debug, Clone, Default)]
pub struct CdclSolver {
    num_vars: usize,
    clauses: Vec<Clause>,
    assignments: BTreeMap<usize, (bool, usize)>,
    decision_level: usize,
    trail: Vec<Literal>,
    learned_clauses: usize,
}

impl CdclSolver {
    #[must_use]
    pub fn new(num_vars: usize) -> Self {
        Self {
            num_vars,
            clauses: Vec::new(),
            assignments: BTreeMap::new(),
            decision_level: 0,
            trail: Vec::new(),
            learned_clauses: 0,
        }
    }

    pub fn add_clause(&mut self, lits: Vec<Literal>) {
        if !lits.is_empty() {
            self.clauses.push(Clause { literals: lits });
        }
    }

    fn value_of(&self, lit: Literal) -> Option<bool> {
        let v = lit.var();
        self.assignments
            .get(&v)
            .map(|(val, _)| if lit.is_positive() { *val } else { !*val })
    }

    fn bcp(&mut self) -> Option<usize> {
        let mut progress = true;
        while progress {
            progress = false;
            for (idx, clause) in self.clauses.iter().enumerate() {
                let mut unassigned = Vec::new();
                let mut satisfied = false;
                for &lit in &clause.literals {
                    match self.value_of(lit) {
                        Some(true) => {
                            satisfied = true;
                            break;
                        }
                        Some(false) => {}
                        None => unassigned.push(lit),
                    }
                }
                if satisfied {
                    continue;
                }
                if unassigned.is_empty() {
                    return Some(idx);
                }
                if unassigned.len() == 1 {
                    if let Some(&unit_lit) = unassigned.first() {
                        let var = unit_lit.var();
                        let val = unit_lit.is_positive();
                        self.assignments.insert(var, (val, self.decision_level));
                        self.trail.push(unit_lit);
                        progress = true;
                    }
                }
            }
        }
        None
    }

    fn pick_branching_literal(&self) -> Option<Literal> {
        for v in 1..=self.num_vars {
            if !self.assignments.contains_key(&v) {
                if let Ok(signed_v) = i32::try_from(v) {
                    return Some(Literal(signed_v));
                }
            }
        }
        None
    }

    fn analyze_conflict(&mut self, conflict_idx: usize) -> (Vec<Literal>, usize) {
        self.learned_clauses = self.learned_clauses.saturating_add(1);
        let mut learned = Vec::new();
        let mut max_backtrack_level = 0;

        if let Some(conflict_clause) = self.clauses.get(conflict_idx) {
            for &lit in &conflict_clause.literals {
                let negated = lit.negate();
                learned.push(negated);
                if let Some((_, level)) = self.assignments.get(&lit.var()) {
                    if *level < self.decision_level && *level > max_backtrack_level {
                        max_backtrack_level = *level;
                    }
                }
            }
        }

        (learned, max_backtrack_level)
    }

    fn backtrack(&mut self, target_level: usize) {
        while let Some(lit) = self.trail.last() {
            let var = lit.var();
            if let Some((_, level)) = self.assignments.get(&var) {
                if *level > target_level {
                    if let Some(popped) = self.trail.pop() {
                        self.assignments.remove(&popped.var());
                    }
                } else {
                    break;
                }
            } else {
                break;
            }
        }
        self.decision_level = target_level;
    }

    pub fn solve(&mut self) -> SatResult {
        if self.bcp().is_some() {
            return SatResult::Unsatisfiable;
        }

        loop {
            let Some(next_lit) = self.pick_branching_literal() else {
                return SatResult::Satisfiable;
            };

            self.decision_level = self.decision_level.saturating_add(1);
            let var = next_lit.var();
            let val = next_lit.is_positive();
            self.assignments.insert(var, (val, self.decision_level));
            self.trail.push(next_lit);

            while let Some(conflict_clause_idx) = self.bcp() {
                if self.decision_level == 0 {
                    return SatResult::Unsatisfiable;
                }
                let (learned, backtrack_level) = self.analyze_conflict(conflict_clause_idx);
                self.backtrack(backtrack_level);
                self.add_clause(learned);
            }
        }
    }

    #[must_use]
    pub fn model(&self) -> BTreeMap<usize, bool> {
        let mut m = BTreeMap::new();
        for (&var, &(val, _)) in &self.assignments {
            m.insert(var, val);
        }
        m
    }

    #[must_use]
    pub fn learned_clauses_count(&self) -> usize {
        self.learned_clauses
    }
}
