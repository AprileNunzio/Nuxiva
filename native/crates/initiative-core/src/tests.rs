use crate::*;

const HOUR: u64 = 3_600_000;

fn catalog() -> Catalog {
    Catalog::from_json(
        r#"{"observers":{
        "login-edit":{"source":"fs","topic":"modified","subject_prefix":"src/login","summary_key":"idea.run_security_checks","value":900,"confidence":800,"level":"propose",
          "action":{"kind":"check","class":"background","priority":5,"budget":{"wall_ms":60000,"tokens":0,"tool_calls":10,"cpu_ms":0},"risk_max":"low","input_template":"security:{subject}"}},
        "build-failed":{"source":"bus","topic":"build.failed","summary_key":"idea.diagnose_build","value":800,"confidence":900,"level":"notify",
          "action":{"kind":"diagnose","class":"interactive","priority":7,"budget":{"wall_ms":30000,"tokens":0,"tool_calls":5,"cpu_ms":0},"risk_max":"none","input_template":"diag:{subject}"}},
        "tidy":{"source":"calendar","topic":"idle","summary_key":"idea.tidy","value":600,"confidence":900,"level":"do_and_tell",
          "action":{"kind":"tidy","class":"maintenance","priority":1,"budget":{"wall_ms":30000,"tokens":0,"tool_calls":1,"cpu_ms":0},"risk_max":"low","input_template":"tidy"}},
        "cleanup":{"source":"fs","topic":"stale","summary_key":"idea.cleanup","value":900,"confidence":900,"level":"propose",
          "action":{"kind":"delete","class":"background","priority":1,"budget":{"wall_ms":30000,"tokens":0,"tool_calls":1,"cpu_ms":0},"risk_max":"high","input_template":"rm:{subject}"}}}}"#,
    )
    .expect("catalog")
}

fn engine() -> Engine {
    Engine::new(Settings::default(), catalog()).expect("engine")
}

fn idle() -> Context {
    Context {
        situation: Situation::Idle,
        voice_free: false,
    }
}

fn edit(path: &str, at: u64) -> Event {
    Event {
        source: Source::Fs,
        topic: "modified".into(),
        subject: path.into(),
        at,
    }
}

#[test]
fn file_change_becomes_a_proposal_on_the_widget() {
    let mut e = engine();
    let out = e
        .observe(&edit("src/login/form.rs", 0), idle(), 0)
        .expect("observe");
    assert_eq!(out.len(), 1);
    assert_eq!(out[0].mode, Mode::Widget);
    assert_eq!(out[0].action.input_ref, "security:src/login/form.rs");
    assert_eq!(out[0].summary_key, "idea.run_security_checks");
    assert!(out[0].score > 0);
    assert_eq!(e.pending().len(), 1);
}

#[test]
fn unrelated_events_and_paths_do_nothing() {
    let mut e = engine();
    assert!(
        e.observe(&edit("docs/readme.md", 0), idle(), 0)
            .expect("a")
            .is_empty()
    );
    let other = Event {
        source: Source::Bus,
        topic: "modified".into(),
        subject: "src/login/x".into(),
        at: 0,
    };
    assert!(e.observe(&other, idle(), 0).expect("b").is_empty());
}

#[test]
fn voice_is_used_only_when_free_and_idle() {
    let mut e = engine();
    let out = e
        .observe(
            &edit("src/login/a.rs", 0),
            Context {
                situation: Situation::Idle,
                voice_free: true,
            },
            0,
        )
        .expect("a");
    assert_eq!(out[0].mode, Mode::Speak);
    let out = e
        .observe(
            &edit("src/login/b.rs", 0),
            Context {
                situation: Situation::Guests,
                voice_free: true,
            },
            0,
        )
        .expect("b");
    assert_eq!(out[0].mode, Mode::Widget);
}

#[test]
fn nothing_surfaces_during_a_conversation_and_it_is_released_after() {
    let mut e = engine();
    let talking = Context {
        situation: Situation::Conversation,
        voice_free: true,
    };
    let out = e
        .observe(&edit("src/login/a.rs", 0), talking, 0)
        .expect("a");
    assert_eq!(out[0].mode, Mode::Diary);
    assert!(e.pending().is_empty());
    assert!(e.tick(talking, 1_000).is_empty());
    let released = e.tick(idle(), 2_000);
    assert_eq!(released.len(), 1);
    assert_eq!(released[0].mode, Mode::Widget);
    assert_eq!(e.pending().len(), 1);
}

#[test]
fn sleeping_and_meeting_costs_suppress_low_value_ideas() {
    let mut e = engine();
    let out = e
        .observe(
            &Event {
                source: Source::Bus,
                topic: "build.failed".into(),
                subject: "app".into(),
                at: 0,
            },
            Context {
                situation: Situation::Sleeping,
                voice_free: true,
            },
            0,
        )
        .expect("a");
    assert_eq!(out[0].mode, Mode::Diary);
}

#[test]
fn duplicates_are_suppressed_for_a_while() {
    let mut e = engine();
    assert_eq!(
        e.observe(&edit("src/login/a.rs", 0), idle(), 0)
            .expect("a")
            .len(),
        1
    );
    assert!(
        e.observe(&edit("src/login/a.rs", 10), idle(), 10)
            .expect("b")
            .is_empty()
    );
    assert_eq!(
        e.observe(&edit("src/login/a.rs", HOUR), idle(), HOUR)
            .expect("c")
            .len(),
        1
    );
}

#[test]
fn hourly_cap_moves_the_rest_to_the_diary() {
    let mut s = Settings::default();
    s.hourly_cap = 3;
    let mut e = Engine::new(s, catalog()).expect("engine");
    let mut surfaced = 0;
    for i in 0..10 {
        let out = e
            .observe(&edit(&format!("src/login/f{i}.rs"), i), idle(), i)
            .expect("o");
        surfaced += out.iter().filter(|p| p.mode != Mode::Diary).count();
    }
    assert_eq!(surfaced, 3);
    assert_eq!(e.stats().capped, 7);
    let later = e
        .observe(&edit("src/login/z.rs", HOUR + 5), idle(), HOUR + 5)
        .expect("later");
    assert_eq!(later[0].mode, Mode::Widget);
}

#[test]
fn accepting_returns_a_valid_task_once() {
    let mut e = engine();
    let id = e.observe(&edit("src/login/a.rs", 0), idle(), 0).expect("a")[0].id;
    let spec = e.accept(id, 1).expect("accept");
    assert!(spec.validate().is_ok());
    assert_eq!(e.accept(id, 2), Err(InitiativeError::NotFound));
    assert_eq!(e.acceptance_permille(), Some(1_000));
}

#[test]
fn refusal_lowers_the_level_for_a_day_then_recovers() {
    let mut e = engine();
    let id = e.observe(&edit("src/login/a.rs", 0), idle(), 0).expect("a")[0].id;
    e.refuse(id, 1).expect("refuse");
    let next = e.observe(&edit("src/login/b.rs", 2), idle(), 2).expect("b");
    assert_eq!(next[0].mode, Mode::Widget);
    let id2 = next[0].id;
    e.refuse(id2, 3).expect("refuse again");
    let third = e.observe(&edit("src/login/c.rs", 4), idle(), 4).expect("c");
    assert_eq!(third[0].mode, Mode::Diary);
    let day = 86_400_000;
    let back = e
        .observe(&edit("src/login/d.rs", day + 10), idle(), day + 10)
        .expect("d");
    assert_eq!(back[0].mode, Mode::Widget);
    assert_eq!(e.acceptance_permille(), Some(0));
}

#[test]
fn proposals_expire() {
    let mut e = engine();
    let id = e.observe(&edit("src/login/a.rs", 0), idle(), 0).expect("a")[0].id;
    assert!(e.tick(idle(), 2 * HOUR).is_empty());
    assert!(e.pending().is_empty());
    assert_eq!(e.stats().expired, 1);
    assert_eq!(e.accept(id, 2 * HOUR), Err(InitiativeError::NotFound));
}

#[test]
fn risky_actions_never_run_without_consent_or_a_rule() {
    let mut e = engine();
    let out = e
        .observe(
            &Event {
                source: Source::Fs,
                topic: "stale".into(),
                subject: "tmp/old".into(),
                at: 0,
            },
            idle(),
            0,
        )
        .expect("a");
    assert_eq!(out[0].mode, Mode::Widget);
    assert!(out[0].requires_consent);
    assert_eq!(e.approve_always("cleanup"), Err(InitiativeError::Consent));
    assert_eq!(e.approve_always("ghost"), Err(InitiativeError::NotFound));
}

#[test]
fn do_and_tell_needs_an_approved_rule_and_low_risk() {
    let mut e = engine();
    let ev = Event {
        source: Source::Calendar,
        topic: "idle".into(),
        subject: "now".into(),
        at: 0,
    };
    assert_eq!(e.observe(&ev, idle(), 0).expect("a")[0].mode, Mode::Widget);
    e.approve_always("tidy").expect("approve");
    let ev2 = Event {
        subject: "later".into(),
        ..ev.clone()
    };
    assert_eq!(
        e.observe(&ev2, idle(), 5).expect("b")[0].mode,
        Mode::Execute
    );
    e.revoke("tidy");
    let ev3 = Event {
        subject: "again".into(),
        ..ev
    };
    assert_eq!(e.observe(&ev3, idle(), 9).expect("c")[0].mode, Mode::Widget);
}

#[test]
fn do_and_tell_never_runs_in_a_conversation() {
    let mut e = engine();
    e.approve_always("tidy").expect("approve");
    let ev = Event {
        source: Source::Calendar,
        topic: "idle".into(),
        subject: "now".into(),
        at: 0,
    };
    let out = e
        .observe(
            &ev,
            Context {
                situation: Situation::Conversation,
                voice_free: false,
            },
            0,
        )
        .expect("a");
    assert_eq!(out[0].mode, Mode::Diary);
}

#[test]
fn catalog_forbids_do_and_tell_for_risky_actions() {
    let text = r#"{"observers":{"x":{"source":"bus","topic":"a","summary_key":"k","value":1,"confidence":1,"level":"do_and_tell",
        "action":{"kind":"k","class":"background","priority":1,"budget":{"wall_ms":1,"tokens":0,"tool_calls":0,"cpu_ms":0},"risk_max":"medium","input_template":"x"}}}}"#;
    assert_eq!(
        Catalog::from_json(text).err(),
        Some(InitiativeError::Catalog)
    );
    assert_eq!(
        Catalog::from_json("{}").err(),
        Some(InitiativeError::Catalog)
    );
    assert_eq!(
        Catalog::from_json("{\"observers\":{}}").err(),
        Some(InitiativeError::Catalog)
    );
}

#[test]
fn hostile_events_are_rejected() {
    let mut e = engine();
    let bad = Event {
        source: Source::Fs,
        topic: "Bad Topic".into(),
        subject: "x".into(),
        at: 0,
    };
    assert_eq!(
        e.observe(&bad, idle(), 0).err(),
        Some(InitiativeError::Invalid)
    );
    let ctrl = Event {
        source: Source::Fs,
        topic: "modified".into(),
        subject: "src/login/\u{0}x".into(),
        at: 0,
    };
    assert_eq!(
        e.observe(&ctrl, idle(), 0).err(),
        Some(InitiativeError::Invalid)
    );
    let long = Event {
        source: Source::Fs,
        topic: "modified".into(),
        subject: "s".repeat(300),
        at: 0,
    };
    assert_eq!(
        e.observe(&long, idle(), 0).err(),
        Some(InitiativeError::Invalid)
    );
    assert_eq!(
        Engine::event_from_json(
            "{\"source\":\"fs\",\"topic\":\"a\",\"subject\":\"b\",\"at\":1,\"x\":1}"
        )
        .err(),
        Some(InitiativeError::Parse)
    );
    assert!(
        Engine::event_from_json("{\"source\":\"fs\",\"topic\":\"a\",\"subject\":\"b\",\"at\":1}")
            .is_ok()
    );
    assert_eq!(
        Engine::event_from_json(&"x".repeat(9_000)).err(),
        Some(InitiativeError::TooLarge)
    );
}

#[test]
fn state_roundtrip_and_tampered_state() {
    let mut e = engine();
    e.approve_always("tidy").expect("approve");
    let id = e.observe(&edit("src/login/a.rs", 0), idle(), 0).expect("a")[0].id;
    e.refuse(id, 1).expect("refuse");
    let text = e.export_state().expect("export");
    let mut back = engine();
    back.import_state(&text).expect("import");
    assert_eq!(back.export_state().expect("again"), text);
    assert_eq!(
        back.import_state(&text.replace("tidy", "cleanup")).err(),
        Some(InitiativeError::Invalid)
    );
    assert_eq!(
        back.import_state("nope").err(),
        Some(InitiativeError::Parse)
    );
}

#[test]
fn settings_fail_closed() {
    assert!(Settings::default().validate().is_ok());
    let mut s = Settings::default();
    s.cost_conversation = 500;
    assert_eq!(s.validate(), Err(InitiativeError::Settings));
    let mut s = Settings::default();
    s.hourly_cap = 0;
    assert_eq!(s.validate(), Err(InitiativeError::Settings));
    assert!(Settings::from_json("{\"x\":1}").is_err());
    let text = serde_json::to_string(&Settings::default()).expect("json");
    assert_eq!(Settings::from_json(&text).expect("rt"), Settings::default());
}

#[test]
fn randomized_scenarios_respect_every_invariant() {
    let mut state = 0xdead_beef_cafe_f00du64;
    let mut next = move || {
        state ^= state << 13;
        state ^= state >> 7;
        state ^= state << 17;
        state
    };
    let mut e = engine();
    let mut now = 0u64;
    let mut surfaced_times: Vec<u64> = Vec::new();
    for step in 0..4_000u64 {
        now += next() % 120_000;
        let situation = [
            Situation::Idle,
            Situation::Conversation,
            Situation::Sleeping,
            Situation::Guests,
            Situation::Meeting,
        ][(next() % 5) as usize];
        let ctx = Context {
            situation,
            voice_free: next() % 2 == 0,
        };
        let event = match next() % 3 {
            0 => edit(&format!("src/login/f{}", next() % 50), now),
            1 => Event {
                source: Source::Fs,
                topic: "stale".into(),
                subject: format!("tmp/{}", next() % 50),
                at: now,
            },
            _ => Event {
                source: Source::Bus,
                topic: "build.failed".into(),
                subject: format!("b{}", next() % 20),
                at: now,
            },
        };
        let mut produced = e.observe(&event, ctx, now).expect("observe");
        produced.extend(e.tick(ctx, now));
        for p in &produced {
            if situation == Situation::Conversation {
                assert_eq!(p.mode, Mode::Diary, "step {step}");
            }
            if p.action.risk_max > nuxiva_taskq_core::Risk::Low {
                assert_ne!(p.mode, Mode::Execute, "step {step}");
            }
            if p.mode != Mode::Diary {
                surfaced_times.push(now);
            }
        }
        for w in surfaced_times.windows(7) {
            assert!(w[6] - w[0] >= HOUR, "cap exceeded at step {step}");
        }
        if next() % 4 == 0 {
            if let Some(id) = e.pending().first().map(|p| p.id) {
                let _ = if next() % 2 == 0 {
                    e.accept(id, now).map(|_| ())
                } else {
                    e.refuse(id, now)
                };
            }
        }
        assert!(e.pending().len() <= 64);
    }
}

#[test]
fn crate_never_touches_files_or_processes() {
    for name in ["engine.rs", "catalog.rs", "settings.rs", "error.rs"] {
        let src = std::fs::read_to_string(
            std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
                .join("src")
                .join(name),
        )
        .expect("src");
        for banned in ["std::fs", "std::process", "std::net", "File::"] {
            assert!(!src.contains(banned), "{name}: {banned}");
        }
    }
}

#[test]
fn error_codes_roundtrip() {
    for code in [
        "initiative.parse",
        "initiative.consent",
        "initiative.serialize",
    ] {
        assert_eq!(InitiativeError::from_code(code).expect("code").code(), code);
    }
}
