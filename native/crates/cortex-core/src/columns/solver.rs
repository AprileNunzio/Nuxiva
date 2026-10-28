use crate::columns::types::{
    AbstractionTier, CognitiveDomain, ColumnResolution, InvariantShortcut,
};
use crate::platform::error::{CortexError, CortexResult};

const EPSILON: f64 = 1e-9;

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct QuadraticProblem {
    pub a: f64,
    pub b: f64,
    pub c: f64,
}

impl QuadraticProblem {
    pub fn validate(a: f64, b: f64, c: f64) -> CortexResult<Self> {
        if !a.is_finite() || !b.is_finite() || !c.is_finite() {
            return Err(CortexError::InvalidExpression);
        }
        if a.abs() < EPSILON && b.abs() < EPSILON {
            return Err(CortexError::EquationUnsolvable);
        }
        Ok(Self { a, b, c })
    }

    #[must_use]
    pub fn pattern_signature(&self) -> String {
        if self.a.abs() < EPSILON {
            return "linear_first_order".to_string();
        }
        if self.b.abs() < EPSILON && (self.c / self.a) <= 0.0 {
            return "pure_symmetric_square".to_string();
        }
        if self.c.abs() < EPSILON {
            return "zero_constant_factorization".to_string();
        }
        let disc = self.b * self.b - 4.0 * self.a * self.c;
        if disc.abs() < EPSILON {
            return "perfect_binomial_square".to_string();
        }
        if (self.a + self.b + self.c).abs() < EPSILON {
            return "unit_root_conservation".to_string();
        }
        "general_quadratic".to_string()
    }
}

pub fn solve_procedural(
    column_id: &str,
    problem: QuadraticProblem,
) -> CortexResult<ColumnResolution> {
    if problem.a.abs() < EPSILON {
        let root = -problem.c / problem.b;
        return Ok(ColumnResolution {
            column_id: column_id.to_string(),
            domain: CognitiveDomain::Algebraic,
            selected_tier: AbstractionTier::Procedural,
            roots: vec![clean_zero(root)],
            steps_executed: 6,
            steps_saved: 0,
            invariant_applied: None,
            confidence: 0.96,
            trace_keys: vec![
                "trace_normalize_linear_terms".to_string(),
                "trace_isolate_variable_lhs".to_string(),
                "trace_divide_by_coefficient".to_string(),
            ],
        });
    }
    let discriminant = problem.b * problem.b - 4.0 * problem.a * problem.c;
    if discriminant < -EPSILON {
        return Err(CortexError::EquationUnsolvable);
    }
    let clamped_disc = discriminant.max(0.0).sqrt();
    let two_a = 2.0 * problem.a;
    let r1 = clean_zero((-problem.b - clamped_disc) / two_a);
    let r2 = clean_zero((-problem.b + clamped_disc) / two_a);
    let roots = ordered_roots(r1, r2);
    Ok(ColumnResolution {
        column_id: column_id.to_string(),
        domain: CognitiveDomain::Algebraic,
        selected_tier: AbstractionTier::Procedural,
        roots,
        steps_executed: 14,
        steps_saved: 0,
        invariant_applied: None,
        confidence: 0.97,
        trace_keys: vec![
            "trace_expand_polynomial_standard".to_string(),
            "trace_compute_discriminant_explicit".to_string(),
            "trace_extract_principal_radical".to_string(),
            "trace_evaluate_quadratic_branches".to_string(),
        ],
    })
}

pub fn solve_canonical(
    column_id: &str,
    problem: QuadraticProblem,
) -> CortexResult<ColumnResolution> {
    if problem.a.abs() < EPSILON {
        return solve_procedural(column_id, problem);
    }
    let half_b_over_a = -problem.b / (2.0 * problem.a);
    let c_over_a = problem.c / problem.a;
    let distance_sq = half_b_over_a * half_b_over_a - c_over_a;
    if distance_sq < -EPSILON {
        return Err(CortexError::EquationUnsolvable);
    }
    let offset = distance_sq.max(0.0).sqrt();
    let r1 = clean_zero(half_b_over_a - offset);
    let r2 = clean_zero(half_b_over_a + offset);
    Ok(ColumnResolution {
        column_id: column_id.to_string(),
        domain: CognitiveDomain::Algebraic,
        selected_tier: AbstractionTier::Canonical,
        roots: ordered_roots(r1, r2),
        steps_executed: 5,
        steps_saved: 9,
        invariant_applied: Some("vieta_spectral_midpoint".to_string()),
        confidence: 0.99,
        trace_keys: vec![
            "trace_project_monic_operator".to_string(),
            "trace_vieta_centroid_decomposition".to_string(),
        ],
    })
}

pub fn solve_invariant(
    column_id: &str,
    problem: QuadraticProblem,
    known_shortcut: Option<&InvariantShortcut>,
) -> CortexResult<ColumnResolution> {
    let signature = problem.pattern_signature();
    let roots_opt = match signature.as_str() {
        "linear_first_order" => Some(vec![clean_zero(-problem.c / problem.b)]),
        "pure_symmetric_square" => {
            let rad = (-problem.c / problem.a).max(0.0).sqrt();
            Some(ordered_roots(clean_zero(-rad), clean_zero(rad)))
        }
        "zero_constant_factorization" => {
            let root = clean_zero(-problem.b / problem.a);
            Some(ordered_roots(0.0, root))
        }
        "perfect_binomial_square" => {
            let root = clean_zero(-problem.b / (2.0 * problem.a));
            Some(vec![root])
        }
        "unit_root_conservation" => {
            let other = clean_zero(problem.c / problem.a);
            Some(ordered_roots(1.0, other))
        }
        _ => None,
    };

    if let Some(roots) = roots_opt {
        return Ok(ColumnResolution {
            column_id: column_id.to_string(),
            domain: CognitiveDomain::Algebraic,
            selected_tier: AbstractionTier::Invariant,
            roots,
            steps_executed: 1,
            steps_saved: 13,
            invariant_applied: Some(signature),
            confidence: 1.0,
            trace_keys: vec!["trace_symmetry_invariant_collapse_o1".to_string()],
        });
    }

    if let Some(shortcut) = known_shortcut {
        let base = solve_canonical(column_id, problem)?;
        return Ok(ColumnResolution {
            column_id: column_id.to_string(),
            domain: CognitiveDomain::Algebraic,
            selected_tier: AbstractionTier::Invariant,
            roots: base.roots,
            steps_executed: 2,
            steps_saved: 12,
            invariant_applied: Some(shortcut.id.clone()),
            confidence: 0.995,
            trace_keys: vec![
                "trace_compiled_synaptic_invariant_hit".to_string(),
                "trace_direct_eigenvalue_projection".to_string(),
            ],
        });
    }

    Err(CortexError::InvariantNotApplicable)
}

fn clean_zero(val: f64) -> f64 {
    if val.abs() < EPSILON {
        0.0
    } else {
        (val * 1_000_000.0).round() / 1_000_000.0
    }
}

fn ordered_roots(r1: f64, r2: f64) -> Vec<f64> {
    if (r1 - r2).abs() < EPSILON {
        vec![r1]
    } else if r1 < r2 {
        vec![r1, r2]
    } else {
        vec![r2, r1]
    }
}
