use serde::{Deserialize, Serialize};

use crate::error::ActionError;

pub const MAX_URL_LEN: usize = 512;
pub const MAX_JEV_STEPS: usize = 32;
pub const JEV_IFRAME_SANDBOX_FLAGS: &str = "allow-scripts allow-forms";
pub const JEV_CSP_POLICY: &str = "default-src 'none'; script-src 'unsafe-inline' https:; style-src 'unsafe-inline' https:; img-src https: data:; connect-src https:; frame-ancestors 'self'; form-action https:";

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct JevFirewallVerdict {
    pub allowed: bool,
    pub sanitized_url: String,
    pub host: String,
    pub sandbox_flags: &'static str,
    pub csp_header: &'static str,
    pub blocked_reason_key: Option<&'static str>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum JevPhase {
    Judge,
    Execute,
    Verify,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum WebActionKind {
    NavigateUrl,
    GoogleSearch,
    TypeInput,
    ClickElement,
    SelectSlot,
    SubmitBooking,
    VerifyDomState,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct JevWebStep {
    pub step_index: usize,
    pub phase: JevPhase,
    pub action: WebActionKind,
    pub target_selector: String,
    pub input_value: String,
    pub expected_signal_key: String,
    pub requires_user_approval: bool,
    pub verified: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct JevWebSessionPlan {
    pub session_id: String,
    pub entry_url: String,
    pub goal_key: String,
    pub current_step: usize,
    pub steps: Vec<JevWebStep>,
    pub completed: bool,
    pub firewall: JevFirewallVerdict,
}

fn sanitize_text(raw: &str, max_len: usize) -> Result<String, ActionError> {
    let trimmed = raw.trim();
    if trimmed.is_empty() || trimmed.len() > max_len {
        return Err(ActionError::InvalidPath(raw.to_owned()));
    }
    if trimmed
        .chars()
        .any(|c| c.is_control() || c == '\0' || c == '\u{202e}')
    {
        return Err(ActionError::InvalidPath(raw.to_owned()));
    }
    Ok(trimmed.to_owned())
}

#[must_use]
pub fn evaluate_jev_firewall(raw_url: &str) -> JevFirewallVerdict {
    let Ok(clean) = sanitize_text(raw_url, MAX_URL_LEN) else {
        return JevFirewallVerdict {
            allowed: false,
            sanitized_url: String::new(),
            host: String::new(),
            sandbox_flags: JEV_IFRAME_SANDBOX_FLAGS,
            csp_header: JEV_CSP_POLICY,
            blocked_reason_key: Some("i18n.jev.firewall.malformed_url"),
        };
    };

    let lower = clean.to_lowercase();
    if !(lower.starts_with("https://") || lower.starts_with("http://")) {
        return JevFirewallVerdict {
            allowed: false,
            sanitized_url: String::new(),
            host: String::new(),
            sandbox_flags: JEV_IFRAME_SANDBOX_FLAGS,
            csp_header: JEV_CSP_POLICY,
            blocked_reason_key: Some("i18n.jev.firewall.forbidden_scheme"),
        };
    }

    let after_scheme = lower
        .strip_prefix("https://")
        .or_else(|| lower.strip_prefix("http://"))
        .unwrap_or("");
    let host_port = after_scheme.split('/').next().unwrap_or("");
    let host_only = host_port.split(':').next().unwrap_or("");

    let is_local_domain = std::path::Path::new(host_only)
        .extension()
        .is_some_and(|ext| ext.eq_ignore_ascii_case("local"));

    let is_private_or_loopback = host_only.is_empty()
        || host_only == "localhost"
        || is_local_domain
        || host_only.starts_with("127.")
        || host_only.starts_with("10.")
        || host_only.starts_with("192.168.")
        || host_only.starts_with("169.254.")
        || host_only.starts_with("172.16.")
        || host_only.starts_with("172.17.")
        || host_only == "0.0.0.0"
        || host_only == "[::1]";

    if is_private_or_loopback {
        return JevFirewallVerdict {
            allowed: false,
            sanitized_url: String::new(),
            host: host_only.to_owned(),
            sandbox_flags: JEV_IFRAME_SANDBOX_FLAGS,
            csp_header: JEV_CSP_POLICY,
            blocked_reason_key: Some("i18n.jev.firewall.private_network_blocked"),
        };
    }

    let suspicious_payload = lower.contains("<script")
        || lower.contains("javascript:")
        || lower.contains("data:text/html")
        || lower.contains("vbscript:");

    if suspicious_payload {
        return JevFirewallVerdict {
            allowed: false,
            sanitized_url: String::new(),
            host: host_only.to_owned(),
            sandbox_flags: JEV_IFRAME_SANDBOX_FLAGS,
            csp_header: JEV_CSP_POLICY,
            blocked_reason_key: Some("i18n.jev.firewall.xss_payload_blocked"),
        };
    }

    JevFirewallVerdict {
        allowed: true,
        sanitized_url: clean,
        host: host_only.to_owned(),
        sandbox_flags: JEV_IFRAME_SANDBOX_FLAGS,
        csp_header: JEV_CSP_POLICY,
        blocked_reason_key: None,
    }
}

pub fn sanitize_zero_trust_url(raw_url: &str) -> Result<String, ActionError> {
    let verdict = evaluate_jev_firewall(raw_url);
    if !verdict.allowed {
        return Err(ActionError::InvalidPath(raw_url.to_owned()));
    }
    Ok(verdict.sanitized_url)
}

fn encode_query_component(q: &str) -> String {
    q.split_whitespace()
        .map(|word| {
            word.chars()
                .filter(|c| c.is_alphanumeric() || *c == '-' || *c == '_')
                .collect::<String>()
        })
        .filter(|w| !w.is_empty())
        .collect::<Vec<_>>()
        .join("+")
}

pub fn build_google_search_jev_plan(
    session_id: &str,
    query: &str,
) -> Result<JevWebSessionPlan, ActionError> {
    let clean_sid = sanitize_text(session_id, 80)?;
    let clean_q = sanitize_text(query, 240)?;
    let encoded = encode_query_component(&clean_q);
    let entry_url = format!("https://www.google.com/search?q={encoded}");
    let firewall = evaluate_jev_firewall(&entry_url);
    if !firewall.allowed {
        return Err(ActionError::InvalidPath(entry_url));
    }

    let steps = vec![
        JevWebStep {
            step_index: 0,
            phase: JevPhase::Judge,
            action: WebActionKind::NavigateUrl,
            target_selector: "window.location".to_owned(),
            input_value: entry_url.clone(),
            expected_signal_key: "i18n.jev.signal.url_validated".to_owned(),
            requires_user_approval: false,
            verified: true,
        },
        JevWebStep {
            step_index: 1,
            phase: JevPhase::Execute,
            action: WebActionKind::GoogleSearch,
            target_selector: "input[name='q']".to_owned(),
            input_value: clean_q.clone(),
            expected_signal_key: "i18n.jev.signal.results_rendered".to_owned(),
            requires_user_approval: false,
            verified: false,
        },
        JevWebStep {
            step_index: 2,
            phase: JevPhase::Verify,
            action: WebActionKind::VerifyDomState,
            target_selector: "#search".to_owned(),
            input_value: clean_q,
            expected_signal_key: "i18n.jev.signal.search_verified".to_owned(),
            requires_user_approval: false,
            verified: false,
        },
    ];

    Ok(JevWebSessionPlan {
        session_id: clean_sid,
        entry_url,
        goal_key: "i18n.jev.goal.google_search".to_owned(),
        current_step: 1,
        steps,
        completed: false,
        firewall,
    })
}

pub fn build_restaurant_booking_jev_plan(
    session_id: &str,
    restaurant_query: &str,
    guests: u8,
    date_time_iso: &str,
) -> Result<JevWebSessionPlan, ActionError> {
    let clean_sid = sanitize_text(session_id, 80)?;
    let clean_rest = sanitize_text(restaurant_query, 180)?;
    let clean_dt = sanitize_text(date_time_iso, 64)?;
    let safe_guests = guests.clamp(1, 20);
    let encoded = encode_query_component(&format!("prenota ristorante {clean_rest}"));
    let entry_url = format!("https://www.google.com/search?q={encoded}");
    let firewall = evaluate_jev_firewall(&entry_url);
    if !firewall.allowed {
        return Err(ActionError::InvalidPath(entry_url));
    }

    let steps = vec![
        JevWebStep {
            step_index: 0,
            phase: JevPhase::Judge,
            action: WebActionKind::GoogleSearch,
            target_selector: "input[name='q']".to_owned(),
            input_value: clean_rest.clone(),
            expected_signal_key: "i18n.jev.signal.restaurant_located".to_owned(),
            requires_user_approval: false,
            verified: true,
        },
        JevWebStep {
            step_index: 1,
            phase: JevPhase::Execute,
            action: WebActionKind::SelectSlot,
            target_selector: "[data-booking-slot]".to_owned(),
            input_value: format!("{safe_guests}p @ {clean_dt}"),
            expected_signal_key: "i18n.jev.signal.table_slot_available".to_owned(),
            requires_user_approval: false,
            verified: false,
        },
        JevWebStep {
            step_index: 2,
            phase: JevPhase::Judge,
            action: WebActionKind::SubmitBooking,
            target_selector: "button[type='submit']".to_owned(),
            input_value: clean_rest,
            expected_signal_key: "i18n.jev.signal.awaiting_final_confirmation".to_owned(),
            requires_user_approval: true,
            verified: false,
        },
        JevWebStep {
            step_index: 3,
            phase: JevPhase::Verify,
            action: WebActionKind::VerifyDomState,
            target_selector: "[data-booking-confirmed]".to_owned(),
            input_value: clean_dt,
            expected_signal_key: "i18n.jev.signal.reservation_confirmed".to_owned(),
            requires_user_approval: false,
            verified: false,
        },
    ];

    Ok(JevWebSessionPlan {
        session_id: clean_sid,
        entry_url,
        goal_key: "i18n.jev.goal.restaurant_booking".to_owned(),
        current_step: 1,
        steps,
        completed: false,
        firewall,
    })
}

pub fn verify_and_advance_jev_step(
    plan: &mut JevWebSessionPlan,
    observed_dom_signal: &str,
    user_approved: bool,
) -> Result<bool, ActionError> {
    let clean_sig = sanitize_text(observed_dom_signal, 240)?;
    let Some(step) = plan.steps.get_mut(plan.current_step) else {
        plan.completed = true;
        return Ok(true);
    };

    if step.requires_user_approval && !user_approved {
        return Ok(false);
    }

    if clean_sig.is_empty() {
        return Ok(false);
    }

    step.verified = true;
    plan.current_step = plan.current_step.saturating_add(1);
    if plan.current_step >= plan.steps.len() {
        plan.completed = true;
    }
    Ok(plan.completed)
}
