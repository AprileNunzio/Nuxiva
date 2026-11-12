use serde::{Deserialize, Serialize};

use crate::error::ThoughtError;

const MAX_QUESTION_LEN: usize = 600;
const MAX_ANSWER_LEN: usize = 1_200;
const VOI_USER_ESCALATION_THRESHOLD_BPS: u32 = 6_500;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum InquiryScope {
    Architecture,
    DataModel,
    SecurityPolicy,
    PaymentAndCompliance,
    UserExperience,
    IntegrationContract,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ResolutionSource {
    AutonomousArchitect,
    SharedContract,
    EscalateToUser,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct DialecticExchange {
    pub id: String,
    pub scope: InquiryScope,
    pub question: String,
    pub answer: String,
    pub resolution: ResolutionSource,
    pub voi_bps: u32,
    pub options: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SocraticReport {
    pub goal: String,
    pub autonomous_decisions: Vec<DialecticExchange>,
    pub user_escalations: Vec<DialecticExchange>,
    pub invariants: Vec<String>,
    pub confidence_bps: u32,
}

#[must_use]
pub fn compute_voi_bps(
    scope: InquiryScope,
    impact_on_schema: u8,
    reversibility: u8,
    goal_mentions_choice: bool,
) -> u32 {
    if goal_mentions_choice {
        return 1_500;
    }
    let base: u32 = match scope {
        InquiryScope::PaymentAndCompliance => 7_500,
        InquiryScope::SecurityPolicy => 5_500,
        InquiryScope::Architecture => 4_500,
        InquiryScope::DataModel => 4_000,
        InquiryScope::IntegrationContract => 3_500,
        InquiryScope::UserExperience => 5_000,
    };
    let impact_bonus = u32::from(impact_on_schema.min(100)).saturating_mul(25);
    let rev_penalty = u32::from(reversibility.min(100)).saturating_mul(20);
    base.saturating_add(impact_bonus)
        .saturating_sub(rev_penalty)
        .min(10_000)
}

#[must_use]
pub fn classify_resolution(voi_bps: u32, has_contract: bool) -> ResolutionSource {
    if has_contract {
        return ResolutionSource::SharedContract;
    }
    if voi_bps >= VOI_USER_ESCALATION_THRESHOLD_BPS {
        ResolutionSource::EscalateToUser
    } else {
        ResolutionSource::AutonomousArchitect
    }
}

fn build_exchange(
    id: &str,
    scope: InquiryScope,
    question: &str,
    default_answer: &str,
    weights: (u8, u8),
    goal_mentions: bool,
    options: Vec<String>,
) -> DialecticExchange {
    let voi_bps = compute_voi_bps(scope, weights.0, weights.1, goal_mentions);
    let resolution = classify_resolution(voi_bps, false);
    DialecticExchange {
        id: id.to_owned(),
        scope,
        question: question.chars().take(MAX_QUESTION_LEN).collect(),
        answer: default_answer.chars().take(MAX_ANSWER_LEN).collect(),
        resolution,
        voi_bps,
        options,
    }
}

fn is_ecommerce_domain(combined: &str) -> bool {
    combined.contains("e-commerce")
        || combined.contains("ecommerce")
        || combined.contains("negozio")
        || combined.contains("shop")
        || combined.contains("carrello")
        || combined.contains("catalogo")
}

fn collect_exchanges(combined: &str, invariants: &mut Vec<String>) -> Vec<DialecticExchange> {
    let mut exchanges = Vec::new();
    if is_ecommerce_domain(combined) {
        let mentions_payment = combined.contains("stripe")
            || combined.contains("paypal")
            || combined.contains("satispay")
            || combined.contains("bonifico");
        exchanges.push(build_exchange(
            "q-payment-gateway",
            InquiryScope::PaymentAndCompliance,
            "Quale gateway di pagamento e flusso fiscale adottare per il checkout?",
            "Architettura modulare PaymentProvider con adapter Stripe predefinito, webhook firmati HMAC e idempotency key sugli ordini.",
            (90, 25),
            mentions_payment,
            vec![
                "Stripe (Carte, Apple Pay, Google Pay)".to_owned(),
                "PayPal + Rateale".to_owned(),
                "Multi-gateway astratto (Stripe + PayPal)".to_owned(),
            ],
        ));
        invariants.push(
            "Idempotenza transazionale sul checkout e calcolo centesimale intero (no float per valute)"
                .to_owned(),
        );
        invariants.push(
            "Riserva atomica dello stock inventario prima della conferma pagamento".to_owned(),
        );
    }

    let mentions_db =
        combined.contains("postgres") || combined.contains("sqlite") || combined.contains("mysql");
    exchanges.push(build_exchange(
        "q-storage-engine",
        InquiryScope::DataModel,
        "Quale strategia di persistenza garantisce coerenza ACID e ricerca istantanea sul catalogo?",
        "Storage relazionale transazionale con indici full-text/trigram per ricerca sotto i 10ms e migrazioni idempotenti.",
        (70, 60),
        mentions_db,
        vec![
            "PostgreSQL con pool asincrono".to_owned(),
            "SQLite in modalita WAL local-first".to_owned(),
        ],
    ));

    let mentions_auth = combined.contains("oauth")
        || combined.contains("jwt")
        || combined.contains("session")
        || combined.contains("pam");
    exchanges.push(build_exchange(
        "q-security-auth",
        InquiryScope::SecurityPolicy,
        "Come proteggere le sessioni utente, il pannello admin e le operazioni sensibili?",
        "Sessioni firmate HMAC HTTP-only con rotazione token, RBAC per ruolo, rate-limiting e CSRF protection su ogni mutazione.",
        (75, 55),
        mentions_auth,
        vec![
            "Sessioni firmate HMAC + RBAC".to_owned(),
            "OAuth2 / OIDC + MFA".to_owned(),
        ],
    ));

    exchanges.push(build_exchange(
        "q-api-contract",
        InquiryScope::IntegrationContract,
        "Come sincronizzare Backend e Frontend senza inconsistenze di tipo?",
        "Contratto formale condiviso nel registro del Cervello Condiviso con schemi tipizzati request/response e test di contratto.",
        (65, 75),
        true,
        vec!["OpenAPI + Schemi Tipizzati Condivisi".to_owned()],
    ));
    exchanges
}

pub fn interrogate_goal(
    goal: &str,
    known_decisions: &[String],
) -> Result<SocraticReport, ThoughtError> {
    let trimmed = goal.trim();
    if trimmed.is_empty() {
        return Err(ThoughtError::InvalidText {
            field: "goal",
            reason: "goal must not be empty",
        });
    }
    let combined = format!(
        "{} {}",
        trimmed.to_lowercase(),
        known_decisions.join(" ").to_lowercase()
    );
    let mut invariants = vec![
        "Zero-trust input validation su tutti i confini API".to_owned(),
        "Modularizzazione rigorosa sotto le 500 righe per file".to_owned(),
        "Persistenza atomica con rollback sicuro e prove verificabili".to_owned(),
    ];
    let exchanges = collect_exchanges(&combined, &mut invariants);

    let mut autonomous_decisions = Vec::new();
    let mut user_escalations = Vec::new();
    for ex in exchanges {
        if ex.resolution == ResolutionSource::EscalateToUser {
            user_escalations.push(ex);
        } else {
            autonomous_decisions.push(ex);
        }
    }

    let penalty = u32::try_from(user_escalations.len())
        .unwrap_or(10)
        .saturating_mul(1_200);
    let confidence_bps = 9_500_u32.saturating_sub(penalty).max(5_000);

    Ok(SocraticReport {
        goal: trimmed.to_owned(),
        autonomous_decisions,
        user_escalations,
        invariants,
        confidence_bps,
    })
}
