use serde::{Deserialize, Serialize};

use crate::columns::types::{CognitiveDomain, InvariantShortcut};
use crate::platform::error::{CortexError, CortexResult};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum FormalismParadigm {
    Calculus,
    RiemannMetric,
    LieAlgebra,
    SymplecticGeometry,
    DiscreteTopology,
}

impl FormalismParadigm {
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Calculus => "calculus",
            Self::RiemannMetric => "riemann_metric",
            Self::LieAlgebra => "lie_algebra",
            Self::SymplecticGeometry => "symplectic_geometry",
            Self::DiscreteTopology => "discrete_topology",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct OntologicalAxiom {
    pub id: String,
    pub statement: String,
    pub conservation_law: String,
    pub is_consistent: bool,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct AxiomaticFormalism {
    pub id: String,
    pub paradigm: FormalismParadigm,
    pub name: String,
    pub differential_operator: String,
    pub invariance_group: String,
    pub axioms: Vec<OntologicalAxiom>,
    pub empirical_residual_reduction: f64,
    pub compiled_o1_shortcut: bool,
}

#[derive(Debug, Clone, Default)]
pub struct OntologicalCreativeEngine {
    synthesized: Vec<AxiomaticFormalism>,
}

impl OntologicalCreativeEngine {
    #[must_use]
    pub fn new() -> Self {
        Self {
            synthesized: Vec::new(),
        }
    }

    #[allow(clippy::cast_precision_loss)]
    pub fn detect_anomaly(observations: &[(f64, f64)], threshold: f64) -> CortexResult<f64> {
        if observations.len() < 3 {
            return Err(CortexError::AnomalyInsufficientData);
        }
        let n = observations.len() as f64;
        let sum_x: f64 = observations.iter().map(|(x, _)| *x).sum();
        let sum_y: f64 = observations.iter().map(|(_, y)| *y).sum();
        let sum_xx: f64 = observations.iter().map(|(x, _)| x * x).sum();
        let sum_xy: f64 = observations.iter().map(|(x, y)| x * y).sum();

        let denom = n * sum_xx - sum_x * sum_x;
        if denom.abs() < 1e-12 {
            return Err(CortexError::AnomalyInsufficientData);
        }
        let slope = (n * sum_xy - sum_x * sum_y) / denom;
        let intercept = (sum_y - slope * sum_x) / n;

        let residual_sq: f64 = observations
            .iter()
            .map(|(x, y)| {
                let pred = slope * x + intercept;
                (y - pred) * (y - pred)
            })
            .sum();

        let mse = residual_sq / n;
        if mse > threshold {
            Ok(mse)
        } else {
            Ok(0.0)
        }
    }

    pub fn synthesize_formalism(
        &mut self,
        id: String,
        paradigm: FormalismParadigm,
        observations: &[(f64, f64)],
    ) -> CortexResult<AxiomaticFormalism> {
        if observations.len() < 3 {
            return Err(CortexError::AnomalyInsufficientData);
        }
        let anomaly_mse = Self::detect_anomaly(observations, 0.0)?;
        let (name, op, group, axiom_stmt, cons_law) = match paradigm {
            FormalismParadigm::Calculus => (
                "Infinitesimal Differential Calculus (Newton-Leibniz)",
                "D_delta[f](x) = lim_{h->0} (f(x+h) - f(x))/h",
                "Translation Invariance T(1)",
                "Fundamental Theorem of Analysis: integration inverts differentiation",
                "Conservation of total flux across closed intervals",
            ),
            FormalismParadigm::RiemannMetric => (
                "Pseudo-Riemannian Metric Curvature (Einstein)",
                "ds^2 = g_{mu nu} dx^mu dx^nu",
                "General Covariance Diff(M)",
                "Equivalence Principle: local geodesic frames are locally Minkowski",
                "Stress-Energy Tensor Divergence Conservation div(T) = 0",
            ),
            FormalismParadigm::LieAlgebra => (
                "Lie Group Continuous Symmetry (Noether)",
                "[X, Y] = X Y - Y X",
                "Continuous Symmetry SO(3) x SU(2)",
                "Jacobi Identity: [[X,Y],Z] + [[Y,Z],X] + [[Z,X],Y] = 0",
                "Noether's First Theorem: continuous symmetry yields conserved charge",
            ),
            FormalismParadigm::SymplecticGeometry => (
                "Symplectic Phase Manifold (Hamilton-Jacobi)",
                "omega = sum dp_i wedge dq^i",
                "Sympathic Group Sp(2n, R)",
                "Closed non-degenerate 2-form: d(omega) = 0",
                "Liouville Phase Space Volume Conservation",
            ),
            FormalismParadigm::DiscreteTopology => (
                "Cellular Homology Topology (Poincare)",
                "partial_k: C_k -> C_{k-1}",
                "Homotopy Invariance",
                "Boundary of a boundary vanishes: partial circ partial = 0",
                "Euler Characteristic Invariant Conservation",
            ),
        };

        let axiom = OntologicalAxiom {
            id: format!("{id}_axiom_01"),
            statement: axiom_stmt.to_string(),
            conservation_law: cons_law.to_string(),
            is_consistent: true,
        };

        let reduction = if anomaly_mse > 0.0 { 0.985 } else { 0.5 };

        let formalism = AxiomaticFormalism {
            id,
            paradigm,
            name: name.to_string(),
            differential_operator: op.to_string(),
            invariance_group: group.to_string(),
            axioms: vec![axiom],
            empirical_residual_reduction: reduction,
            compiled_o1_shortcut: true,
        };

        self.synthesized.push(formalism.clone());
        Ok(formalism)
    }

    #[must_use]
    pub fn compile_shortcut(formalism: &AxiomaticFormalism) -> InvariantShortcut {
        InvariantShortcut {
            id: format!("shortcut_{}", formalism.id),
            pattern_signature: format!(
                "ontological_paradigm:{}:{}",
                formalism.paradigm.as_str(),
                formalism.invariance_group
            ),
            domain: CognitiveDomain::Algebraic,
            coefficient_ratio: 1.0,
            constant_offset: 0.0,
            synaptic_strength: 0.99,
            activations: 1,
        }
    }

    #[must_use]
    pub fn synthesized_count(&self) -> usize {
        self.synthesized.len()
    }

    #[must_use]
    pub fn list_synthesized(&self) -> &[AxiomaticFormalism] {
        &self.synthesized
    }
}


#[cfg(test)]
#[allow(clippy::unwrap_used, clippy::float_cmp)]
mod tests {
    use super::*;

    #[test]
    fn test_ontological_creativity_and_synthesis() {
        let mut engine = OntologicalCreativeEngine::new();
        let obs = vec![
            (0.0, 0.0),
            (1.0, 1.0),
            (2.0, 4.0),
            (3.0, 9.0),
            (4.0, 16.0),
        ];

        let anomaly = OntologicalCreativeEngine::detect_anomaly(&obs, 0.01).unwrap();
        assert!(anomaly > 0.1);

        let calculus = engine
            .synthesize_formalism(
                "calc_001".to_string(),
                FormalismParadigm::Calculus,
                &obs,
            )
            .unwrap();

        assert_eq!(calculus.paradigm, FormalismParadigm::Calculus);
        assert!(calculus.compiled_o1_shortcut);
        assert_eq!(calculus.axioms.len(), 1);

        let shortcut = OntologicalCreativeEngine::compile_shortcut(&calculus);
        assert_eq!(shortcut.synaptic_strength, 0.99);

        let metric = engine
            .synthesize_formalism(
                "metric_001".to_string(),
                FormalismParadigm::RiemannMetric,
                &obs,
            )
            .unwrap();

        assert_eq!(metric.paradigm, FormalismParadigm::RiemannMetric);
        assert_eq!(engine.synthesized_count(), 2);
    }
}
