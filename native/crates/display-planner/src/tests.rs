use crate::candidate::{Candidate, Size};
use crate::category::known_widgets;
use crate::context::{Context, Mode, Previous, Screen};
use crate::grid::Slot;
use crate::nucleus::Form;
use crate::plan::{Input, Placed, ScenePlan, plan};
use crate::policy::PlannerPolicy;
use crate::select::Reason;
use nuxiva_display_domain::{AudienceKind, Sensitivity};

pub fn cand(key: &str, widget: &str) -> Candidate {
    Candidate {
        key: key.into(),
        widget: widget.into(),
        category: None,
        importance: 60,
        urgency: 0,
        sensitivity: Sensitivity::Public,
        owner: None,
        size: Size::M,
        cost: 1.0,
        exclusive: None,
        media: None,
        source: None,
        forced: false,
        intent: false,
        pinned: None,
        needs_webgl2: false,
        quarantined: false,
        guest_safe: false,
        relevance: 0.0,
        preference: 0.0,
        age_ms: 0,
        ttl_ms: None,
        interacted_ms: None,
    }
}

pub fn ctx(audience: AudienceKind, mode: Mode) -> Context {
    Context {
        audience,
        present: vec!["nunzio".into()],
        alone: true,
        mode,
        guest_public: false,
        trust_guests: false,
        cap: None,
    }
}

pub fn screen() -> Screen {
    Screen {
        id: 0,
        aspect: 16.0 / 9.0,
        role: None,
        webgl2: true,
        budget: 12.0,
    }
}

pub fn run(
    candidates: Vec<Candidate>,
    context: Context,
    previous: Previous,
    now_ms: u64,
) -> ScenePlan {
    let input = Input {
        screen: screen(),
        context,
        candidates,
        previous,
        now_ms,
    };
    plan(&input, &PlannerPolicy::default())
        .unwrap_or_else(|_| unreachable!("politica predefinita non valida"))
}

fn shown(p: &ScenePlan) -> Vec<&str> {
    p.shown.iter().map(|s| s.key.as_str()).collect()
}

fn reason(p: &ScenePlan, key: &str) -> Option<Reason> {
    p.explain.iter().find(|e| e.key == key).map(|e| e.reason)
}

#[test]
fn an_empty_scene_keeps_the_hero_nucleus() {
    let p = run(
        Vec::new(),
        ctx(AudienceKind::Empty, Mode::Ambient),
        Previous::default(),
        0,
    );
    assert_eq!(p.nucleus.form, Form::CoreHero);
    assert_eq!(p.shown, [] as [Placed; 0]);
}

#[test]
fn conversation_with_weather_and_music_shows_three_widgets() {
    let mut music = cand("music", "music");
    music.media = Some("audio".into());
    let mut reply = cand("reply", "text_short");
    reply.intent = true;
    let p = run(
        vec![cand("weather", "weather"), music, reply],
        ctx(AudienceKind::Authorized, Mode::Conversation),
        Previous::default(),
        0,
    );
    assert_eq!(p.shown.len(), 3);
    assert_eq!(p.nucleus.form, Form::CoreHero);
}

#[test]
fn a_guest_removes_personal_widgets_even_during_dwell() {
    let mut health = cand("health", "health_hub");
    health.sensitivity = Sensitivity::Personal;
    health.owner = Some("nunzio".into());
    let mut previous = Previous::default();
    previous.shown.insert(
        "health".into(),
        (
            Slot {
                col: 0,
                row: 0,
                w: 4,
                h: 3,
            },
            0,
        ),
    );
    let p = run(
        vec![health, cand("weather", "weather")],
        ctx(AudienceKind::Mixed, Mode::Ambient),
        previous,
        1_000,
    );
    assert_eq!(shown(&p), vec!["weather"]);
    assert_eq!(reason(&p, "health"), Some(Reason::Privacy));
}

#[test]
fn sensitive_widgets_need_the_owner_alone() {
    let mut bank = cand("bank", "document_viewer");
    bank.sensitivity = Sensitivity::Sensitive;
    bank.owner = Some("nunzio".into());
    let mut context = ctx(AudienceKind::Authorized, Mode::Ambient);
    context.alone = false;
    assert_eq!(
        reason(
            &run(vec![bank.clone()], context, Previous::default(), 0),
            "bank"
        ),
        Some(Reason::Privacy)
    );
    bank.owner = Some("anna".into());
    assert_eq!(
        reason(
            &run(
                vec![bank],
                ctx(AudienceKind::Authorized, Mode::Ambient),
                Previous::default(),
                0
            ),
            "bank"
        ),
        Some(Reason::Privacy)
    );
}

#[test]
fn a_video_takeover_turns_the_nucleus_into_a_pill() {
    let mut tv = cand("tv", "tv_player");
    tv.size = Size::Full;
    tv.intent = true;
    let mut alarm = cand("alarm", "alarm");
    alarm.urgency = 3;
    let p = run(
        vec![tv, cand("weather", "weather"), alarm],
        ctx(AudienceKind::Authorized, Mode::Ambient),
        Previous::default(),
        0,
    );
    assert_eq!(p.nucleus.form, Form::WhisperPill);
    assert_eq!(reason(&p, "weather"), Some(Reason::Takeover));
    assert!(shown(&p).contains(&"alarm"));
}

#[test]
fn crowding_shrinks_the_nucleus_before_dropping_widgets() {
    let many: Vec<Candidate> = (0..6)
        .map(|i| {
            let mut c = cand(&format!("w{i}"), "code_view");
            c.size = Size::L;
            c.forced = true;
            c
        })
        .collect();
    let p = run(
        many,
        ctx(AudienceKind::Authorized, Mode::Project),
        Previous::default(),
        0,
    );
    assert_ne!(p.nucleus.form, Form::CoreHero);
    assert!(p.explain.iter().any(|e| e.reason == Reason::Space) || p.shown.len() == 6);
}

#[test]
fn conflicts_are_resolved() {
    let (mut tv, mut cam) = (cand("a", "tv_player"), cand("b", "cam_stream"));
    tv.exclusive = Some("video".into());
    cam.exclusive = Some("video".into());
    tv.importance = 90;
    let (mut big, mut badge) = (cand("c", "weather"), cand("d", "weather"));
    big.source = Some("meteo".into());
    badge.source = Some("meteo".into());
    badge.importance = 60;
    big.importance = 70;
    let (mut music, mut karaoke) = (cand("e", "music"), cand("f", "karaoke"));
    music.media = Some("audio".into());
    karaoke.media = Some("audio".into());
    music.importance = 80;
    let mut context = ctx(AudienceKind::Authorized, Mode::Ambient);
    context.cap = Some(10);
    let p = run(
        vec![tv, cam, big, badge, music, karaoke],
        context,
        Previous::default(),
        0,
    );
    assert_eq!(reason(&p, "b"), Some(Reason::Exclusive));
    assert_eq!(reason(&p, "d"), Some(Reason::Merged));
    assert!(p.shown.iter().any(|s| s.key == "f" && s.muted));
    assert!(p.shown.iter().any(|s| s.key == "e" && !s.muted));
}

#[test]
fn caps_and_budget_limit_optional_widgets() {
    let five: Vec<Candidate> = (0..5).map(|i| cand(&format!("i{i}"), "weather")).collect();
    let p = run(
        five,
        ctx(AudienceKind::Authorized, Mode::Ambient),
        Previous::default(),
        0,
    );
    assert_eq!(p.shown.len(), 4);
    assert_eq!(
        p.explain
            .iter()
            .filter(|e| e.reason == Reason::Cognitive)
            .count(),
        1
    );
    let mut heavy = cand("heavy", "studio_3d");
    heavy.cost = 20.0;
    heavy.importance = 100;
    let p = run(
        vec![heavy],
        ctx(AudienceKind::Authorized, Mode::Ambient),
        Previous::default(),
        0,
    );
    assert_eq!(reason(&p, "heavy"), Some(Reason::Budget));
}

#[test]
fn hysteresis_and_dwell_keep_the_scene_still() {
    let mut weak = cand("weak", "clock");
    weak.importance = 20;
    assert_eq!(
        reason(
            &run(
                vec![weak.clone()],
                ctx(AudienceKind::Authorized, Mode::Ambient),
                Previous::default(),
                0
            ),
            "weak"
        ),
        Some(Reason::Threshold)
    );
    let mut previous = Previous::default();
    let slot = Slot {
        col: 0,
        row: 0,
        w: 4,
        h: 3,
    };
    previous.shown.insert("weak".into(), (slot, 0));
    let p = run(
        vec![weak.clone()],
        ctx(AudienceKind::Authorized, Mode::Ambient),
        previous.clone(),
        60_000,
    );
    assert_eq!(shown(&p), vec!["weak"]);
    assert_eq!(p.shown.first().and_then(|s| s.slot), Some(slot));
    weak.importance = 0;
    weak.cost = 6.0;
    let p = run(
        vec![weak.clone()],
        ctx(AudienceKind::Authorized, Mode::Ambient),
        previous.clone(),
        4_000,
    );
    assert_eq!(shown(&p), vec!["weak"]);
    assert_eq!(
        reason(
            &run(
                vec![weak],
                ctx(AudienceKind::Authorized, Mode::Ambient),
                previous,
                60_000
            ),
            "weak"
        ),
        Some(Reason::Threshold)
    );
}

#[test]
fn pinned_positions_are_constraints() {
    let mut pinned = cand("pin", "weather");
    let slot = Slot {
        col: 8,
        row: 0,
        w: 4,
        h: 3,
    };
    pinned.pinned = Some(slot);
    let p = run(
        vec![pinned],
        ctx(AudienceKind::Authorized, Mode::Ambient),
        Previous::default(),
        0,
    );
    assert_eq!(p.shown.first().and_then(|s| s.slot), Some(slot));
}

#[test]
fn quarantine_and_capability_filters_apply() {
    let mut q = cand("q", "weather");
    q.quarantined = true;
    let mut g = cand("g", "studio_3d");
    g.needs_webgl2 = true;
    let mut input = Input {
        screen: screen(),
        context: ctx(AudienceKind::Authorized, Mode::Ambient),
        candidates: vec![q, g],
        previous: Previous::default(),
        now_ms: 0,
    };
    input.screen.webgl2 = false;
    let p = plan(&input, &PlannerPolicy::default()).unwrap_or_else(|_| unreachable!());
    assert_eq!(reason(&p, "q"), Some(Reason::Quarantine));
    assert_eq!(reason(&p, "g"), Some(Reason::Capability));
}

#[test]
fn invalid_policies_and_inputs_are_rejected() {
    let policy = PlannerPolicy {
        enter: 0.1,
        exit: 0.5,
        ..PlannerPolicy::default()
    };
    let input = Input {
        screen: screen(),
        context: ctx(AudienceKind::Empty, Mode::Ambient),
        candidates: Vec::new(),
        previous: Previous::default(),
        now_ms: 0,
    };
    assert!(plan(&input, &policy).is_err());
    assert!(serde_json::from_str::<Candidate>(r#"{"key":"a","widget":"b","admin":true}"#).is_err());
}

#[test]
fn every_installed_widget_has_a_category() {
    let dir =
        std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../../../installer_wizard/widgets");
    let Ok(entries) = std::fs::read_dir(dir) else {
        return;
    };
    let known: Vec<&str> = known_widgets().collect();
    for entry in entries.flatten() {
        if entry.path().join("widget.json").exists() {
            let name = entry.file_name().to_string_lossy().to_string();
            assert!(known.contains(&name.as_str()), "{name}");
        }
    }
}
