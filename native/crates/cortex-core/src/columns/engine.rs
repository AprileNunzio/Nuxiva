use serde::{Deserialize, Serialize};

use crate::columns::solver::{
    QuadraticProblem, solve_canonical, solve_invariant, solve_procedural,
};
use crate::columns::types::{
    AbstractionTier, CognitiveDomain, ColumnResolution, CorticalColumnSpec, InvariantShortcut,
};
use crate::platform::error::{CortexError, CortexResult};
use crate::platform::sanitizer::sanitize_identifier;

pub const MAX_COLUMNS: usize = 256;
pub const MAX_SHORTCUTS: usize = 1024;
const PROMOTION_STEP: f32 = 0.04;
const MAX_SNAPSHOT_LEN: usize = 16_777_216;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CorticalCortex {
    columns: Vec<CorticalColumnSpec>,
    shortcuts: Vec<InvariantShortcut>,
}

impl Default for CorticalCortex {
    fn default() -> Self {
        Self::new()
    }
}

impl CorticalCortex {
    #[must_use]
    pub fn new() -> Self {
        let columns = vec![
            CorticalColumnSpec {
                id: "col_algebra_sym".to_string(),
                domain: CognitiveDomain::Algebraic,
                preferred_tier: AbstractionTier::Invariant,
                maturity_score: 0.88,
                total_executions: 12,
                shortcuts_consolidated: 4,
            },
            CorticalColumnSpec {
                id: "col_logic_sat".to_string(),
                domain: CognitiveDomain::LogicalSat,
                preferred_tier: AbstractionTier::Canonical,
                maturity_score: 0.76,
                total_executions: 8,
                shortcuts_consolidated: 2,
            },
            CorticalColumnSpec {
                id: "col_kinematic_ik".to_string(),
                domain: CognitiveDomain::KinematicControl,
                preferred_tier: AbstractionTier::Invariant,
                maturity_score: 0.82,
                total_executions: 19,
                shortcuts_consolidated: 5,
            },
            CorticalColumnSpec {
                id: "col_causal_dag".to_string(),
                domain: CognitiveDomain::CausalGraph,
                preferred_tier: AbstractionTier::Canonical,
                maturity_score: 0.71,
                total_executions: 6,
                shortcuts_consolidated: 1,
            },
        ];
        let shortcuts = vec![
            InvariantShortcut {
                id: "inv_unit_root_sum".to_string(),
                pattern_signature: "unit_root_conservation".to_string(),
                domain: CognitiveDomain::Algebraic,
                coefficient_ratio: 1.0,
                constant_offset: 0.0,
                synaptic_strength: 0.95,
                activations: 7,
            },
            InvariantShortcut {
                id: "inv_symmetric_dipole".to_string(),
                pattern_signature: "pure_symmetric_square".to_string(),
                domain: CognitiveDomain::Algebraic,
                coefficient_ratio: -1.0,
                constant_offset: 0.0,
                synaptic_strength: 0.92,
                activations: 5,
            },
        ];
        Self { columns, shortcuts }
    }

    #[must_use]
    pub fn columns(&self) -> &[CorticalColumnSpec] {
        &self.columns
    }

    #[must_use]
    pub fn shortcuts(&self) -> &[InvariantShortcut] {
        &self.shortcuts
    }

    pub fn solve_quadratic(
        &mut self,
        column_id: &str,
        a: f64,
        b: f64,
        c: f64,
        requested_tier: Option<AbstractionTier>,
    ) -> CortexResult<ColumnResolution> {
        let clean_id = sanitize_identifier(column_id)?;
        let problem = QuadraticProblem::validate(a, b, c)?;
        let signature = problem.pattern_signature();
        let col_idx = self
            .columns
            .iter()
            .position(|col| col.id == clean_id)
            .ok_or(CortexError::UnknownNeuron)?;

        let effective_tier = match requested_tier {
            Some(tier) => tier,
            None => self
                .columns
                .get(col_idx)
                .map_or(AbstractionTier::Canonical, |c| c.preferred_tier),
        };

        let matching_shortcut = self
            .shortcuts
            .iter()
            .find(|s| s.pattern_signature == signature)
            .cloned();

        let resolution = match effective_tier {
            AbstractionTier::Procedural => solve_procedural(&clean_id, problem)?,
            AbstractionTier::Canonical => solve_canonical(&clean_id, problem)?,
            AbstractionTier::Invariant => {
                match solve_invariant(&clean_id, problem, matching_shortcut.as_ref()) {
                    Ok(res) => res,
                    Err(CortexError::InvariantNotApplicable) => {
                        let fallback = solve_canonical(&clean_id, problem)?;
                        self.consolidate_shortcut(&signature, a, b, c)?;
                        if let Some(col) = self.columns.get_mut(col_idx) {
                            col.shortcuts_consolidated =
                                col.shortcuts_consolidated.saturating_add(1);
                        }
                        fallback
                    }
                    Err(err) => return Err(err),
                }
            }
        };

        if let Some(col) = self.columns.get_mut(col_idx) {
            col.total_executions = col.total_executions.saturating_add(1);
            col.maturity_score = (col.maturity_score + PROMOTION_STEP).min(1.0);
            if col.maturity_score >= 0.85 {
                col.preferred_tier = AbstractionTier::Invariant;
            }
        }

        if let Some(applied_id) = &resolution.invariant_applied {
            if let Some(sc) = self
                .shortcuts
                .iter_mut()
                .find(|s| &s.id == applied_id || &s.pattern_signature == applied_id)
            {
                sc.activations = sc.activations.saturating_add(1);
                sc.synaptic_strength = (sc.synaptic_strength + 0.02).min(1.0);
            }
        }

        Ok(resolution)
    }

    pub fn consolidate_shortcut(
        &mut self,
        pattern_signature: &str,
        a: f64,
        b: f64,
        c: f64,
    ) -> CortexResult<InvariantShortcut> {
        let sig = sanitize_identifier(pattern_signature)?;
        if let Some(existing) = self
            .shortcuts
            .iter_mut()
            .find(|s| s.pattern_signature == sig)
        {
            existing.activations = existing.activations.saturating_add(1);
            existing.synaptic_strength = (existing.synaptic_strength + 0.03).min(1.0);
            return Ok(existing.clone());
        }
        if self.shortcuts.len() >= MAX_SHORTCUTS {
            return Err(CortexError::CapacityExceeded);
        }
        let ratio = if a.abs() > 1e-9 { -b / a } else { 0.0 };
        let offset = if a.abs() > 1e-9 { c / a } else { c };
        let shortcut = InvariantShortcut {
            id: format!("inv_{sig}"),
            pattern_signature: sig,
            domain: CognitiveDomain::Algebraic,
            coefficient_ratio: ratio,
            constant_offset: offset,
            synaptic_strength: 0.84,
            activations: 1,
        };
        self.shortcuts.push(shortcut.clone());
        Ok(shortcut)
    }

    pub fn snapshot_json(&self) -> CortexResult<String> {
        serde_json::to_string(self).map_err(|_| CortexError::SnapshotInvalid)
    }

    pub fn from_snapshot_json(snapshot: &str) -> CortexResult<Self> {
        if snapshot.is_empty() || snapshot.len() > MAX_SNAPSHOT_LEN {
            return Err(CortexError::SnapshotInvalid);
        }
        serde_json::from_str(snapshot).map_err(|_| CortexError::SnapshotInvalid)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn invariant_tier_solves_in_one_step() {
        let mut cortex = CorticalCortex::new();
        let res = cortex.solve_quadratic(
            "col_algebra_sym",
            1.0,
            -5.0,
            4.0,
            Some(AbstractionTier::Invariant),
        );
        assert!(res.is_ok());
        if let Ok(val) = res {
            assert_eq!(val.selected_tier, AbstractionTier::Invariant);
            assert_eq!(val.steps_executed, 1);
            assert_eq!(val.roots, vec![1.0, 4.0]);
        }
    }

    #[test]
    fn general_quadratic_consolidates_shortcut_for_next_run() {
        let mut cortex = CorticalCortex::new();
        let first = cortex.solve_quadratic(
            "col_algebra_sym",
            2.0,
            -7.0,
            3.0,
            Some(AbstractionTier::Invariant),
        );
        assert!(first.is_ok());
        let second = cortex.solve_quadratic(
            "col_algebra_sym",
            2.0,
            -7.0,
            3.0,
            Some(AbstractionTier::Invariant),
        );
        assert!(second.is_ok());
        if let Ok(val) = second {
            assert_eq!(val.selected_tier, AbstractionTier::Invariant);
            assert_eq!(val.steps_executed, 2);
        }
    }
}
