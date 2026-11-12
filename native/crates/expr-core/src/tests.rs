use std::collections::HashMap;

use crate::{Fault, Host, Value, evaluate, float_repr};

#[derive(Default)]
struct Names {
    vars: HashMap<String, Value>,
    calls: Vec<String>,
}

impl Host for Names {
    fn name(&mut self, name: &str) -> Result<Option<Value>, Fault> {
        Ok(self.vars.get(name).cloned())
    }

    fn call(&mut self, name: &str, args: Vec<Value>) -> Result<Value, Fault> {
        self.calls.push(name.to_owned());
        match name {
            "state" => Ok(Value::Str(format!(
                "on:{}",
                args.first().map(Value::py_str).unwrap_or_default()
            ))),
            _ => Err(Fault::Host),
        }
    }
}

fn names(pairs: &[(&str, Value)]) -> Names {
    let mut n = Names::default();
    for (k, v) in pairs {
        n.vars.insert((*k).to_owned(), v.clone());
    }
    for f in [
        "num", "int", "str", "len", "round", "min", "max", "sum", "upper", "join", "contains",
        "abs", "state",
    ] {
        n.vars.insert(f.to_owned(), Value::Func(f.to_owned()));
    }
    n
}

fn ev(src: &str, n: &mut Names) -> Result<Value, Fault> {
    evaluate(src, n)
}

fn ok(src: &str) -> Value {
    ev(src, &mut names(&[])).unwrap_or(Value::Opaque("errore".to_owned()))
}

fn denied(src: &str) -> bool {
    matches!(
        ev(src, &mut names(&[("x", Value::Int(1))])),
        Err(Fault::Expr(_))
    )
}

#[test]
fn arithmetic_follows_python() {
    assert_eq!(ok("2 + 3 * 4"), Value::Int(14));
    assert_eq!(ok("7 // -2"), Value::Int(-4));
    assert_eq!(ok("-7 % 3"), Value::Int(2));
    assert_eq!(ok("7 % -3"), Value::Int(-2));
    assert_eq!(ok("7 / 2"), Value::Float(3.5));
    assert_eq!(ok("-7.5 // 2"), Value::Float(-4.0));
    assert_eq!(ok("2 ** 10"), Value::Int(1024));
    assert_eq!(ok("2 ** 1000"), Value::Int(1_i128 << 64));
    assert_eq!(ok("2 ** -1"), Value::Float(0.5));
    assert_eq!(ok("True + True"), Value::Int(2));
    assert_eq!(ok("'a' + 1"), Value::Str("a1".to_owned()));
    assert_eq!(ok("'3' * 2"), Value::Float(6.0));
    assert_eq!(
        ok("[1, 2] * 2"),
        Value::List(vec![
            Value::Int(1),
            Value::Int(2),
            Value::Int(1),
            Value::Int(2)
        ])
    );
    assert!(
        matches!(ev("1 / 0", &mut names(&[])), Err(Fault::Expr(m)) if m == "divisione per zero")
    );
    assert!(denied("[0] * 100000"));
}

#[test]
fn logic_comparisons_and_names() {
    let mut n = names(&[("x", Value::Int(5)), ("y", Value::Str("a".to_owned()))]);
    assert_eq!(ev("x > 3 and y == 'a'", &mut n), Ok(Value::Bool(true)));
    assert_eq!(
        ev("'sì' if x else 'no'", &mut n),
        Ok(Value::Str("sì".to_owned()))
    );
    assert_eq!(ev("'26' > 25", &mut n), Ok(Value::Bool(true)));
    assert_eq!(ev("1 < x < 10", &mut n), Ok(Value::Bool(true)));
    assert_eq!(ev("0 or '' or 'z'", &mut n), Ok(Value::Str("z".to_owned())));
    assert_eq!(ev("mai_impostata", &mut n), Ok(Value::Null));
    assert_eq!(ev("vero and not falso", &mut n), Ok(Value::Bool(true)));
    assert_eq!(ev("x is None", &mut n), Ok(Value::Bool(false)));
    assert_eq!(
        ev(
            "'a' in 'casa' and 2 in [1, 2] and 'k' not in {'j': 1}",
            &mut n
        ),
        Ok(Value::Bool(true))
    );
    assert_eq!(ev("1 == 1.0 == True", &mut n), Ok(Value::Bool(true)));
}

#[test]
fn data_access_and_builtins() {
    let data = Value::Map(vec![
        (Value::Str("to".to_owned()), Value::Str("on".to_owned())),
        (
            Value::Str("list".to_owned()),
            Value::List(vec![Value::Int(3), Value::Int(9)]),
        ),
    ]);
    let mut n = names(&[("data", data)]);
    assert_eq!(ev("data.to", &mut n), Ok(Value::Str("on".to_owned())));
    assert_eq!(ev("data['list'][-1]", &mut n), Ok(Value::Int(9)));
    assert_eq!(ev("data.missing", &mut n), Ok(Value::Null));
    assert_eq!(ev("data['list'][5]", &mut n), Ok(Value::Null));
    assert_eq!(
        ev("max(data['list']) + min(4, 2)", &mut n),
        Ok(Value::Int(11))
    );
    assert_eq!(ev("sum(data['list'])", &mut n), Ok(Value::Int(12)));
    assert_eq!(ev("round(2.675, 2)", &mut n), Ok(Value::Float(2.67)));
    assert_eq!(ev("round('2,5')", &mut n), Ok(Value::Float(2.0)));
    assert_eq!(ev("int('7,9')", &mut n), Ok(Value::Int(7)));
    assert_eq!(ev("num('x', 3)", &mut n), Ok(Value::Int(3)));
    assert_eq!(
        ev("upper('ok') + str(1.0) + str([1, 'a'])", &mut n),
        Ok(Value::Str("OK1.0[1, 'a']".to_owned()))
    );
    assert_eq!(
        ev("join(['a', 1], '-') + str(len('città'))", &mut n),
        Ok(Value::Str("a-15".to_owned()))
    );
    assert_eq!(
        ev("contains('Salotto', 'LOT')", &mut n),
        Ok(Value::Bool(true))
    );
    assert_eq!(
        ev("state('light.x')", &mut n),
        Ok(Value::Str("on:light.x".to_owned()))
    );
    assert_eq!(n.calls, ["state"]);
    assert!(
        matches!(ev("ignota(1)", &mut n), Err(Fault::Expr(m)) if m == "funzione sconosciuta: ignota")
    );
}

#[test]
fn forbidden_constructs_and_limits() {
    for bad in [
        "__import__('os')",
        "(lambda: 1)()",
        "x.__class__",
        "[i for i in range(3)]",
        "open('f')",
        "x[1:2]",
        "f'{x}'",
        "{1, 2}",
        "x := 3",
        "~x",
        "x | 1",
        "len(*[1])",
        "round(x, ndigits=2)",
        "x.upper()",
    ] {
        assert!(denied(bad), "{bad}");
    }
    assert!(denied(&"1 + ".repeat(300)));
    assert!(denied(&format!("{}1{}", "(".repeat(150), ")".repeat(150))));
    assert!(denied(&"[".repeat(120)));
    assert_eq!(ok("False and x.y()"), Value::Bool(false));
}

#[test]
fn literals_and_repr() {
    assert_eq!(ok("0x1F + 0b11 + 0o7 + 1_000"), Value::Int(1041));
    assert_eq!(ok("'a\\tb' 'c'"), Value::Str("a\tbc".to_owned()));
    assert_eq!(ok("r'a\\n'"), Value::Str("a\\n".to_owned()));
    assert_eq!(ok("'\\u00e8'"), Value::Str("è".to_owned()));
    assert_eq!(
        ok("(1, 2)"),
        Value::List(vec![Value::Int(1), Value::Int(2)])
    );
    assert_eq!(
        ok("{'a': 1, 'a': 2}"),
        Value::Map(vec![(Value::Str("a".to_owned()), Value::Int(2))])
    );
    for (f, s) in [
        (1.0, "1.0"),
        (0.1, "0.1"),
        (1e16, "1e+16"),
        (1.5e-5, "1.5e-05"),
        (123_456.789, "123456.789"),
        (1e-4, "0.0001"),
    ] {
        assert_eq!(float_repr(f), s);
    }
}
