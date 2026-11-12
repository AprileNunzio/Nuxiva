use serde::{Deserialize, Serialize};

use crate::error::ThoughtError;

pub const MAX_SPECIALISTS: usize = 16;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SpecialistProfile {
    pub id: String,
    pub title: String,
    pub department: String,
    pub mission: String,
    pub skills: Vec<String>,
    pub permissions: Vec<String>,
}

fn make_specialist(
    id: &str,
    title: &str,
    department: &str,
    mission: &str,
    skills: &[&str],
    permissions: &[&str],
) -> SpecialistProfile {
    SpecialistProfile {
        id: id.to_owned(),
        title: title.to_owned(),
        department: department.to_owned(),
        mission: mission.to_owned(),
        skills: skills.iter().map(|s| (*s).to_owned()).collect(),
        permissions: permissions.iter().map(|p| (*p).to_owned()).collect(),
    }
}

fn append_domain_specialists(combined: &str, roster: &mut Vec<SpecialistProfile>) {
    let needs_frontend = [
        "sito",
        "web",
        "ui",
        "frontend",
        "e-commerce",
        "ecommerce",
        "vetrina",
        "dashboard",
        "react",
        "svelte",
    ]
    .iter()
    .any(|kw| combined.contains(kw));
    if needs_frontend {
        roster.push(make_specialist(
            "frontend",
            "Luca · Lead Frontend & UX Engineer",
            "Design & Interfacce",
            "Costruisce interfacce responsive, accessibili, multilingua i18n con stato reattivo e componenti modulari.",
            &["responsive-ui", "typescript-react", "state-management", "i18n-locale", "accessibility"],
            &["read", "write", "execute"],
        ));
    }

    let needs_commerce = [
        "e-commerce",
        "ecommerce",
        "negozio",
        "carrello",
        "checkout",
        "pagament",
        "informatica",
    ]
    .iter()
    .any(|kw| combined.contains(kw));
    if needs_commerce {
        roster.push(make_specialist(
            "commerce_specialist",
            "Giulia · Commerce & Payment Specialist",
            "Ingegneria Transazionale",
            "Progetta catalogo prodotti, filtri tecnici hardware, carrello persistente, calcolo IVA centesimale e checkout idempotente.",
            &["catalog-search", "cart-state-machine", "payment-webhooks", "inventory-locking", "tax-engine"],
            &["read", "write", "execute", "forge"],
        ));
    }

    let needs_3d = ["3d", "webgl", "three", "shader", "gioco", "isometric"]
        .iter()
        .any(|kw| combined.contains(kw));
    if needs_3d {
        roster.push(make_specialist(
            "graphics_3d",
            "Matteo · 3D & WebGL Specialist",
            "Design & Interfacce 3D",
            "Sviluppa scene 3D performanti, asset pipeline, controlli camera e shader ottimizzati.",
            &[
                "three-webgl",
                "shader-pipeline",
                "scene-graph",
                "frame-budget",
            ],
            &["read", "write", "execute"],
        ));
    }
}

pub fn recruit_specialists(
    goal: &str,
    architecture: &str,
) -> Result<Vec<SpecialistProfile>, ThoughtError> {
    if goal.trim().is_empty() {
        return Err(ThoughtError::InvalidText {
            field: "goal",
            reason: "goal must not be empty",
        });
    }
    let combined = format!("{} {}", goal.to_lowercase(), architecture.to_lowercase());
    let mut roster = vec![
        make_specialist(
            "architect",
            "Marco · System Architect",
            "Architettura & Core",
            "Progetta il DAG modulare, i contratti formali API/dati e garantisce il limite di 500 righe per file.",
            &[
                "clean-architecture",
                "dag-design",
                "rust-core",
                "api-contracts",
                "zero-trust",
            ],
            &["read", "write"],
        ),
        make_specialist(
            "backend",
            "Sofia · Senior Backend Engineer",
            "Ingegneria Backend",
            "Implementa la logica di dominio, le API ad alte prestazioni, la persistenza transazionale e la gestione errori.",
            &[
                "rust-tokio",
                "python-fastapi",
                "sql-transactions",
                "rest-api",
                "concurrency",
            ],
            &["read", "write", "execute", "forge"],
        ),
    ];

    append_domain_specialists(&combined, &mut roster);

    roster.push(make_specialist(
        "security",
        "Chiara · Security & Zero-Trust Lead",
        "Qualita & Sicurezza",
        "Verifica autenticazione, autorizzazione, protezione OWASP Top 10, sanitizzazione input e isolamento sandbox.",
        &["zero-trust", "owasp-top10", "hmac-crypto", "rbac-policy", "sandbox-guard"],
        &["read", "execute"],
    ));
    roster.push(make_specialist(
        "qa",
        "Elena · QA & Adversarial Verifier",
        "Qualita & Sicurezza",
        "Valida ogni criterio di accettazione con test end-to-end riproducibili, edge-case e prove crittografiche.",
        &["e2e-testing", "adversarial-testing", "proof-verification", "regression-suite"],
        &["read", "write", "execute"],
    ));

    if ["deploy", "docker", "systemd", "ci", "server"]
        .iter()
        .any(|kw| combined.contains(kw))
    {
        roster.push(make_specialist(
            "devops",
            "Davide · DevOps & Reliability Engineer",
            "Infrastruttura & Deploy",
            "Automatizza pipeline CI/CD, servizi systemd, containerizzazione e rollback sicuro.",
            &["systemd-daemon", "ci-cd", "observability", "auto-rollback"],
            &["read", "write", "execute"],
        ));
    }

    roster.truncate(MAX_SPECIALISTS);
    Ok(roster)
}
