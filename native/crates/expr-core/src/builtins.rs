use std::cmp::Ordering;

use crate::Fault;
use crate::eval::{MAX_TEXT, binary};
use crate::parser::Bin;
use crate::value::{Value, number, parse_number};

fn err(name: &str) -> Fault {
    Fault::Expr(format!("argomenti non validi per {name}"))
}

fn arity(name: &str, args: &[Value], lo: usize, hi: usize) -> Result<(), Fault> {
    if args.len() < lo || args.len() > hi {
        Err(err(name))
    } else {
        Ok(())
    }
}

fn arg(args: &[Value], i: usize) -> &Value {
    args.get(i).unwrap_or(&Value::Null)
}

fn items(name: &str, value: &Value) -> Result<Vec<Value>, Fault> {
    match value {
        Value::List(items) => Ok(items.clone()),
        Value::Str(s) => Ok(s.chars().map(|c| Value::Str(c.to_string())).collect()),
        Value::Map(pairs) => Ok(pairs.iter().map(|(k, _)| k.clone()).collect()),
        _ => Err(err(name)),
    }
}

#[allow(clippy::many_single_char_names)]
fn order(name: &str, a: &Value, b: &Value) -> Result<Ordering, Fault> {
    match (a, b) {
        (Value::Str(x), Value::Str(y)) => Ok(x.cmp(y)),
        (x, y) if x.is_numeric() && y.is_numeric() => match (x.as_int(), y.as_int()) {
            (Some(p), Some(q)) => Ok(p.cmp(&q)),
            _ => x
                .as_f64()
                .unwrap_or(0.0)
                .partial_cmp(&y.as_f64().unwrap_or(0.0))
                .ok_or_else(|| err(name)),
        },
        (Value::List(x), Value::List(y)) => {
            for (p, q) in x.iter().zip(y) {
                if !p.py_eq(q) {
                    return order(name, p, q);
                }
            }
            Ok(x.len().cmp(&y.len()))
        }
        _ => Err(err(name)),
    }
}

fn extreme(name: &str, args: &[Value], want: Ordering) -> Result<Value, Fault> {
    let pool = if args.len() == 1 {
        items(name, arg(args, 0))?
    } else {
        args.to_vec()
    };
    let mut iter = pool.into_iter();
    let mut best = iter.next().ok_or_else(|| err(name))?;
    for v in iter {
        if order(name, &v, &best)? == want {
            best = v;
        }
    }
    Ok(best)
}

fn round_to(value: f64, digits: i128) -> f64 {
    if !value.is_finite() {
        return value;
    }
    if digits == 0 {
        return value.round_ties_even();
    }
    if (1..=300).contains(&digits) {
        let places = usize::try_from(digits).unwrap_or(0);
        return format!("{value:.places$}").parse().unwrap_or(value);
    }
    if digits > 300 {
        return value;
    }
    let scale = 10_f64.powi(i32::try_from(digits.saturating_neg()).unwrap_or(i32::MAX));
    if !scale.is_finite() {
        return 0.0_f64.copysign(value);
    }
    (value / scale).round_ties_even() * scale
}

#[allow(clippy::cast_possible_truncation)]
fn to_int(name: &str, v: f64) -> Result<Value, Fault> {
    if !v.is_finite() || v.abs() >= 1.0e38 {
        return Err(err(name));
    }
    Ok(Value::Int(v.trunc() as i128))
}

fn text(value: String) -> Result<Value, Fault> {
    if value.len() > MAX_TEXT {
        return Err(Fault::Expr("risultato troppo grande".to_owned()));
    }
    Ok(Value::Str(value))
}

#[must_use]
pub fn call(name: &str, args: &[Value]) -> Option<Result<Value, Fault>> {
    let out = match name {
        "num" | "float" => arity(name, args, 1, 2).map(|()| {
            parse_number(arg(args, 0)).map_or_else(
                || args.get(1).cloned().unwrap_or(Value::Float(0.0)),
                Value::Float,
            )
        }),
        "int" => arity(name, args, 1, 1).and_then(|()| to_int(name, number(arg(args, 0), 0.0))),
        "str" => arity(name, args, 0, 1)
            .and_then(|()| text(args.first().map(Value::py_str).unwrap_or_default())),
        "bool" => {
            arity(name, args, 0, 1).map(|()| Value::Bool(args.first().is_some_and(Value::truthy)))
        }
        "len" => arity(name, args, 1, 1).and_then(|()| match arg(args, 0) {
            Value::Str(s) => Ok(Value::Int(i128::try_from(s.chars().count()).unwrap_or(0))),
            Value::List(l) => Ok(Value::Int(i128::try_from(l.len()).unwrap_or(0))),
            Value::Map(m) => Ok(Value::Int(i128::try_from(m.len()).unwrap_or(0))),
            _ => Err(err(name)),
        }),
        "round" => arity(name, args, 1, 2).and_then(|()| {
            let digits = match args.get(1) {
                None => 0,
                Some(d) => match to_int(name, number(d, 0.0))? {
                    Value::Int(i) => i,
                    _ => 0,
                },
            };
            Ok(Value::Float(round_to(number(arg(args, 0), 0.0), digits)))
        }),
        "abs" => arity(name, args, 1, 1).and_then(|()| match arg(args, 0) {
            Value::Bool(_) | Value::Int(_) => arg(args, 0)
                .as_int()
                .and_then(i128::checked_abs)
                .map(Value::Int)
                .ok_or_else(|| err(name)),
            Value::Float(f) => Ok(Value::Float(f.abs())),
            _ => Err(err(name)),
        }),
        "min" => extreme(name, args, Ordering::Less),
        "max" => extreme(name, args, Ordering::Greater),
        "sum" => arity(name, args, 1, 2).and_then(|()| {
            let mut total = args.get(1).cloned().unwrap_or(Value::Int(0));
            for v in items(name, arg(args, 0))? {
                if !v.is_numeric() || !total.is_numeric() {
                    return Err(err(name));
                }
                total = binary(Bin::Add, total, v)?;
            }
            Ok(total)
        }),
        "lower" => {
            arity(name, args, 1, 1).and_then(|()| text(arg(args, 0).py_str().to_lowercase()))
        }
        "upper" => {
            arity(name, args, 1, 1).and_then(|()| text(arg(args, 0).py_str().to_uppercase()))
        }
        "sqrt" => arity(name, args, 1, 1).and_then(|()| {
            let v = number(arg(args, 0), 0.0);
            if v < 0.0 {
                Err(err(name))
            } else {
                Ok(Value::Float(v.sqrt()))
            }
        }),
        "contains" => arity(name, args, 2, 2).map(|()| {
            Value::Bool(
                arg(args, 0)
                    .py_str()
                    .to_lowercase()
                    .contains(&arg(args, 1).py_str().to_lowercase()),
            )
        }),
        "join" => arity(name, args, 1, 2).and_then(|()| {
            let sep = match args.get(1) {
                None => ", ".to_owned(),
                Some(Value::Str(s)) => s.clone(),
                Some(_) => return Err(err(name)),
            };
            let parts: Vec<String> = items(name, arg(args, 0))?
                .iter()
                .map(Value::py_str)
                .collect();
            text(parts.join(&sep))
        }),
        _ => return None,
    };
    Some(out)
}
