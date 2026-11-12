use crate::capability::Capability;
use crate::cell::Cell;
use crate::decide::{Request, Strength, Verdict, decide};
use crate::matrix::{DEFAULT_JSON, Matrix};
use crate::role::Role;
use serde_json::Value;

const ROLES: [Role; 6] = [
    Role::Owner,
    Role::Family,
    Role::Staff,
    Role::Child,
    Role::Guest,
    Role::Anonymous,
];

fn request(
    caps: &[Capability],
    role: Role,
    strength: Strength,
    local: Option<bool>,
    own: bool,
) -> Request<'_> {
    Request {
        capabilities: caps,
        role,
        strength,
        local,
        own,
    }
}

#[test]
fn every_cell_has_a_positive_and_a_negative_case() {
    let Ok(matrix) = Matrix::builtin() else {
        unreachable!("matrice predefinita non valida");
    };
    for (key, cells) in matrix.export() {
        let Ok(cap) = Capability::parse(&key) else {
            continue;
        };
        let list = [cap];
        for (role, name) in ROLES.iter().zip(cells) {
            let cell = Cell::parse(name).unwrap_or(Cell::Deny);
            let best = decide(
                &request(&list, *role, Strength::Strong, Some(true), true),
                &matrix,
            );
            let worst = decide(
                &request(&list, *role, Strength::None, Some(false), false),
                &matrix,
            );
            match cell {
                Cell::Allow => assert_eq!(
                    (best, worst),
                    (Verdict::Allow, Verdict::Allow),
                    "{key} {role:?}"
                ),
                Cell::Room | Cell::Own | Cell::Strong => {
                    assert_eq!(best, Verdict::Allow, "{key} {role:?}");
                    assert_ne!(worst, Verdict::Allow, "{key} {role:?}");
                }
                Cell::Confirm => {
                    assert_eq!(best, Verdict::Confirm, "{key} {role:?}");
                    assert_eq!(
                        worst,
                        Verdict::NeedProof(Strength::Single),
                        "{key} {role:?}"
                    );
                }
                Cell::Deny => {
                    assert!(matches!(best, Verdict::Deny(_)), "{key} {role:?}");
                    assert!(matches!(worst, Verdict::Deny(_)), "{key} {role:?}");
                }
            }
        }
    }
}

fn relaxed() -> String {
    let mut data: Value = serde_json::from_str(DEFAULT_JSON).unwrap_or(Value::Null);
    if let Some(rules) = data.get_mut("rules").and_then(Value::as_object_mut) {
        for row in rules.values_mut() {
            *row = Value::from(vec!["allow"; 6]);
        }
    }
    data.to_string()
}

#[test]
fn an_override_cannot_open_the_floors_to_guests() {
    let Ok(matrix) = Matrix::parse(&relaxed()) else {
        unreachable!("override non valido");
    };
    for cap in [
        "home.lock.unlock",
        "home.alarm.disarm",
        "comm.message.send",
        "people.health.read",
        "system.admin.manage",
    ] {
        let list = [Capability::parse(cap).unwrap_or_else(|_| {
            Capability::parse("risk.critical").unwrap_or_else(|_| unreachable!())
        })];
        for role in [Role::Guest, Role::Anonymous] {
            assert!(
                matches!(
                    decide(
                        &request(&list, role, Strength::Strong, Some(true), true),
                        &matrix
                    ),
                    Verdict::Deny(_)
                ),
                "{cap}"
            );
        }
    }
    let unlock = [Capability::parse("home.lock.unlock").unwrap_or_else(|_| unreachable!())];
    assert_eq!(
        decide(
            &request(&unlock, Role::Owner, Strength::Single, None, true),
            &matrix
        ),
        Verdict::NeedProof(Strength::Strong)
    );
    let wildcard = r#"{"version":1,"rules":{"risk.critical":["allow","allow","allow","allow","allow","allow"],"home.*":["allow","allow","allow","allow","allow","allow"]}}"#;
    let Ok(open) = Matrix::parse(wildcard) else {
        unreachable!("jolly non valido");
    };
    assert!(matches!(
        decide(
            &request(&unlock, Role::Guest, Strength::Strong, None, true),
            &open
        ),
        Verdict::Deny(_)
    ));
}

#[test]
fn malformed_matrices_are_rejected() {
    for raw in [
        "{}",
        r#"{"version":2,"rules":{"risk.critical":["deny","deny","deny","deny","deny","deny"]}}"#,
        r#"{"version":1,"rules":{"home.light.set":["allow","allow","allow","allow","allow","allow"]}}"#,
        r#"{"version":1,"rules":{"risk.critical":["deny","deny"]}}"#,
        r#"{"version":1,"rules":{"risk.critical":["deny","deny","deny","deny","deny","nope"]}}"#,
        r#"{"version":1,"rules":{"risk.critical":["deny","deny","deny","deny","deny","deny"],"BAD":["deny","deny","deny","deny","deny","deny"]}}"#,
        r#"{"version":1,"extra":1,"rules":{"risk.critical":["deny","deny","deny","deny","deny","deny"]}}"#,
    ] {
        assert!(Matrix::parse(raw).is_err(), "{raw}");
    }
}
