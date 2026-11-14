use crate::*;

fn digest(seed: u8) -> String {
    hex(&[seed; 32])
}

fn draft(path: &str, seed: u8) -> ArtifactDraft {
    ArtifactDraft {
        schema_version: SCHEMA_VERSION,
        files: vec![FileEntry {
            path: path.into(),
            bytes: 10,
            digest: digest(seed),
        }],
    }
}

fn check(name: &str, passed: bool, log: &str) -> Check {
    Check {
        name: name.into(),
        passed,
        severity: if passed {
            Severity::Info
        } else {
            Severity::High
        },
        log: log.into(),
    }
}

fn all_pass() -> Vec<Check> {
    vec![
        check("test", true, ""),
        check("lint", true, ""),
        check("security", true, ""),
    ]
}

fn report(
    artifact: &Artifact,
    iteration: u32,
    checks: Vec<Check>,
    verdict: Verdict,
) -> CriticReport {
    CriticReport {
        schema_version: SCHEMA_VERSION,
        digest: artifact.digest.clone(),
        sandbox_run: format!("run-{iteration}"),
        checks,
        verdict,
        iteration,
    }
}

#[test]
fn gate_never_authorizes_without_a_matching_passed_permit() {
    let gate = Gate::new(Settings::default()).expect("gate");
    let s = Settings::default();
    let artifact = Artifact::seal(draft("src/app.rs", 1), &s).expect("artifact");
    let rep = report(&artifact, 1, all_pass(), Verdict::Pass);
    let passed = Outcome::Passed {
        artifact: artifact.clone(),
        report: rep,
        iterations: 1,
    };
    let failed = Outcome::Exhausted {
        iterations: 5,
        fingerprint: None,
    };
    assert!(gate.issue(&failed).is_none());
    assert_eq!(
        gate.authorize(None, &artifact.digest, &Target::Local, true),
        Decision::Denied
    );
    let permit = gate.issue(&passed).expect("permit");
    assert_eq!(
        gate.authorize(Some(&permit), &artifact.digest, &Target::Local, false),
        Decision::Allowed
    );
    assert_eq!(
        gate.authorize(Some(&permit), &digest(9), &Target::Local, true),
        Decision::Denied
    );
    gate.revoke(&artifact.digest);
    assert_eq!(
        gate.authorize(Some(&permit), &artifact.digest, &Target::Local, true),
        Decision::Denied
    );
    let other = Gate::new(Settings::default()).expect("other");
    assert_eq!(
        other.authorize(Some(&permit), &artifact.digest, &Target::Local, true),
        Decision::Denied
    );
}

#[test]
fn remote_push_needs_consent_unless_repo_is_declared_autonomous() {
    let mut s = Settings::default();
    s.autonomous_repos = vec!["me/free".into()];
    let gate = Gate::new(s.clone()).expect("gate");
    let artifact = Artifact::seal(draft("src/app.rs", 1), &s).expect("artifact");
    let passed = Outcome::Passed {
        artifact: artifact.clone(),
        report: report(&artifact, 1, all_pass(), Verdict::Pass),
        iterations: 1,
    };
    let permit = gate.issue(&passed).expect("permit");
    let free = Target::Remote {
        repo: "me/free".into(),
    };
    let other = Target::Remote {
        repo: "me/other".into(),
    };
    assert_eq!(
        gate.authorize(Some(&permit), &artifact.digest, &free, false),
        Decision::Allowed
    );
    assert_eq!(
        gate.authorize(Some(&permit), &artifact.digest, &other, false),
        Decision::NeedsConsent
    );
    assert_eq!(
        gate.authorize(Some(&permit), &artifact.digest, &other, true),
        Decision::Allowed
    );
    assert_eq!(
        gate.authorize(
            Some(&permit),
            &artifact.digest,
            &Target::Remote {
                repo: "bad repo".into()
            },
            true
        ),
        Decision::Denied
    );
    assert_eq!(gate.audit().len(), 4);
}

#[test]
fn audit_is_bounded() {
    let mut s = Settings::default();
    s.audit_cap = 3;
    let gate = Gate::new(s).expect("gate");
    for _ in 0..10 {
        gate.authorize(None, &digest(1), &Target::Local, false);
    }
    assert_eq!(gate.audit().len(), 3);
}
