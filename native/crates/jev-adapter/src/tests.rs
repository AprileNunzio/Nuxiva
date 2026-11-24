use model_router::Sensitivity;

use crate::{
    Adapter, Attachments, BREAKER_COOLDOWN_MS, BREAKER_FAILURES, Classifier, Input, Node, Platform,
    Reason, Route, Unavailable,
};

struct Fake {
    answer: Result<bool, Unavailable>,
    calls: u32,
}

impl Classifier for Fake {
    fn is_simple(&mut self, _text: &str) -> Result<bool, Unavailable> {
        self.calls += 1;
        self.answer
    }
}

fn simple() -> Fake {
    Fake {
        answer: Ok(true),
        calls: 0,
    }
}

fn node(id: &str, platform: &str) -> Node {
    Node {
        id: id.into(),
        platform: Platform::parse(platform),
    }
}

fn input(text: &str) -> Input<'_> {
    Input {
        text,
        sensitivity: Sensitivity::Public,
        attachments: Attachments::NONE,
    }
}

fn adapter() -> Adapter {
    Adapter::new(
        true,
        [Platform::Windows, Platform::MacOs, Platform::Android],
        ["pc".to_owned(), "mac".to_owned(), "phone".to_owned()],
    )
}

#[test]
fn platform_names_are_recognised() {
    assert_eq!(Platform::parse(" Windows "), Platform::Windows);
    assert_eq!(Platform::parse("Darwin"), Platform::MacOs);
    assert_eq!(Platform::parse("android"), Platform::Android);
    assert_eq!(Platform::parse("plan9"), Platform::Other);
}

#[test]
fn simple_public_requests_go_to_jev_on_all_three_platforms() {
    let mut a = adapter();
    for (id, os) in [("pc", "windows"), ("mac", "macos"), ("phone", "android")] {
        let mut fake = simple();
        assert_eq!(
            a.route(&node(id, os), &input("che ora è"), &mut fake, 0),
            Route::Jev
        );
    }
}

#[test]
fn every_gate_falls_back_to_the_deep_planner_without_asking_the_classifier() {
    let mut fake = simple();
    let long = "a".repeat(769);
    let mut private = input("la mia password");
    private.sensitivity = Sensitivity::Private;
    let mut image = input("guarda");
    image.attachments = Attachments::IMAGE;
    let mut context = input("riassumi");
    context.attachments = Attachments::CONTEXT.with(Attachments::RESULTS);
    let mut a = adapter();
    let cases = [
        (node("pc", "windows"), input(&long), Reason::TooLong),
        (node("pc", "windows"), private, Reason::NotPublic),
        (node("pc", "windows"), image, Reason::RichInput),
        (node("pc", "windows"), context, Reason::RichInput),
        (
            node("other", "windows"),
            input("ciao"),
            Reason::NodeNotEnabled,
        ),
        (
            node("pc", "linux"),
            input("ciao"),
            Reason::UnsupportedPlatform,
        ),
        (node("", "windows"), input("ciao"), Reason::NodeNotEnabled),
    ];
    for (n, i, reason) in cases {
        assert_eq!(a.route(&n, &i, &mut fake, 0), Route::Deep(reason));
    }
    let mut no_key = Adapter::new(false, [Platform::Windows], ["pc".to_owned()]);
    assert_eq!(
        no_key.route(&node("pc", "windows"), &input("ciao"), &mut fake, 0),
        Route::Deep(Reason::NoKey)
    );
    assert_eq!(fake.calls, 0);
}

#[test]
fn complex_requests_are_not_sent_to_jev() {
    let mut fake = Fake {
        answer: Ok(false),
        calls: 0,
    };
    assert_eq!(
        adapter().route(
            &node("pc", "windows"),
            &input("pianifica un viaggio"),
            &mut fake,
            0
        ),
        Route::Deep(Reason::NotSimple)
    );
}

#[test]
fn repeated_failures_open_the_breaker_and_it_closes_after_the_cooldown() {
    let mut a = adapter();
    let n = node("pc", "windows");
    let mut broken = Fake {
        answer: Err(Unavailable),
        calls: 0,
    };
    for _ in 0..BREAKER_FAILURES {
        assert_eq!(
            a.route(&n, &input("ciao"), &mut broken, 1_000),
            Route::Deep(Reason::Unavailable)
        );
    }
    let before = broken.calls;
    assert_eq!(
        a.route(&n, &input("ciao"), &mut broken, 2_000),
        Route::Deep(Reason::BreakerOpen)
    );
    assert_eq!(broken.calls, before);
    let mut healthy = simple();
    assert_eq!(
        a.route(
            &n,
            &input("ciao"),
            &mut healthy,
            1_000 + BREAKER_COOLDOWN_MS
        ),
        Route::Jev
    );
}

#[test]
fn a_success_resets_the_failure_count() {
    let mut a = adapter();
    let n = node("pc", "windows");
    let mut broken = Fake {
        answer: Err(Unavailable),
        calls: 0,
    };
    for _ in 0..BREAKER_FAILURES - 1 {
        a.route(&n, &input("ciao"), &mut broken, 0);
    }
    a.route(&n, &input("ciao"), &mut simple(), 0);
    for _ in 0..BREAKER_FAILURES - 1 {
        a.route(&n, &input("ciao"), &mut broken, 0);
    }
    assert_eq!(a.route(&n, &input("ciao"), &mut simple(), 0), Route::Jev);
}

#[test]
fn a_broken_node_does_not_affect_the_others() {
    let mut a = adapter();
    let mut broken = Fake {
        answer: Err(Unavailable),
        calls: 0,
    };
    for _ in 0..BREAKER_FAILURES {
        a.route(&node("pc", "windows"), &input("ciao"), &mut broken, 0);
    }
    assert_eq!(
        a.route(&node("mac", "macos"), &input("ciao"), &mut simple(), 1),
        Route::Jev
    );
}
