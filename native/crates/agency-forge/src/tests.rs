use std::collections::BTreeMap;

use serde_json::json;

use crate::{
    ForgeCatalog, ForgeError, ForgedToolSpec, ToolStatus, ToolTestCase, diagnose_failure,
    inspect_tool_source, values_equivalent,
};

fn sample_spec(name: &str, code: &str) -> ForgedToolSpec {
    let mut args1 = BTreeMap::new();
    args1.insert("price".to_owned(), json!(100));
    let mut args2 = BTreeMap::new();
    args2.insert("price".to_owned(), json!(200));

    ForgedToolSpec {
        name: name.to_owned(),
        description: "Calcola prezzo ivato".to_owned(),
        args_schema: BTreeMap::from([("price".to_owned(), "prezzo netto".to_owned())]),
        code: code.to_owned(),
        tests: vec![
            ToolTestCase {
                args: args1,
                expect: json!(122),
            },
            ToolTestCase {
                args: args2,
                expect: json!(244),
            },
        ],
        project_id: "ecom-1".to_owned(),
        task_id: "t-checkout".to_owned(),
    }
}

#[test]
fn guard_accepts_pure_python_and_rejects_dangerous_constructs() {
    let valid = "import math\ndef run(args):\n    return math.floor(args['price'] * 1.22)\n";
    let verdict = inspect_tool_source(valid);
    assert!(verdict.is_ok());
    if let Ok(v) = verdict {
        assert_eq!(v.allowed_imports_used, vec!["math".to_owned()]);
    }

    let evil_import = "import subprocess\ndef run(args):\n    return 1\n";
    assert!(matches!(
        inspect_tool_source(evil_import),
        Err(ForgeError::GuardRejected(_))
    ));

    let evil_builtin = "def run(args):\n    return eval(args['x'])\n";
    let err = inspect_tool_source(evil_builtin);
    assert!(err.is_err());
    if let Err(e) = err {
        let diag = diagnose_failure(&e);
        assert!(diag.recoverable);
        assert_eq!(diag.category, "security_guard");
    }
}

#[test]
fn catalog_manages_lifecycle_versioning_and_auto_quarantine() {
    let mut catalog = ForgeCatalog::new();
    let code = "def run(args):\n    return int(args['price'] * 1.22)\n";
    let proposed = catalog.propose(sample_spec("calc_vat", code));
    assert!(proposed.is_ok());
    if let Ok(p) = proposed {
        assert_eq!(p.version, 1);
        assert_eq!(p.status, ToolStatus::Proposed);
        assert!(!p.is_callable());
    }

    assert!(catalog.record_execution("calc_vat", true, None).is_err());

    let approved = catalog.approve("calc_vat");
    assert!(approved.is_ok());
    assert_eq!(catalog.active_tools().len(), 1);

    let _ = catalog.record_execution("calc_vat", false, Some("err 1"));
    let _ = catalog.record_execution("calc_vat", false, Some("err 2"));
    let q = catalog.record_execution("calc_vat", false, Some("err 3"));
    assert!(q.is_ok());
    if let Ok(quarantined) = q {
        assert_eq!(quarantined.status, ToolStatus::Quarantined);
        assert!(!quarantined.is_callable());
    }
    assert_eq!(catalog.active_tools().len(), 0);
}

#[test]
fn values_equivalent_handles_float_tolerance_and_nested_objects() {
    let a = json!({"total": 122.000_000_000_1_f64, "items": [1, 2]});
    let b = json!({"total": 122.0_f64, "items": [1, 2]});
    assert!(values_equivalent(&a, &b));
}
