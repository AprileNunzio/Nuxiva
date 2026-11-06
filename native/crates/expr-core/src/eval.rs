use crate::builtins;
use crate::parser::{Bin, Cmp, Node, Unary};
use crate::value::{Value, insert, lookup, number};
use crate::{Fault, Host};

pub const MAX_STEPS: usize = 2000;
pub const MAX_ITEMS: usize = 10_000;
pub const MAX_TEXT: usize = 100_000;
const MAX_EXP: i128 = 64;

fn err(msg: impl Into<String>) -> Fault {
    Fault::Expr(msg.into())
}

pub struct Evaluator<'h, H: Host> {
    host: &'h mut H,
    steps: usize,
}

fn checked_len(len: usize) -> Result<(), Fault> {
    if len > MAX_ITEMS {
        Err(err("risultato troppo grande"))
    } else {
        Ok(())
    }
}

fn int_or_float(value: Option<i128>, fallback: impl FnOnce() -> f64) -> Value {
    value.map_or_else(|| Value::Float(fallback()), Value::Int)
}

#[allow(clippy::cast_precision_loss)]
fn arith_int(op: Bin, a: i128, b: i128) -> Result<Value, Fault> {
    let fa = a as f64;
    let fb = b as f64;
    Ok(match op {
        Bin::Add => int_or_float(a.checked_add(b), || fa + fb),
        Bin::Sub => int_or_float(a.checked_sub(b), || fa - fb),
        Bin::Mul => int_or_float(a.checked_mul(b), || fa * fb),
        Bin::Div => {
            if b == 0 {
                return Err(err("divisione per zero"));
            }
            Value::Float(fa / fb)
        }
        Bin::FloorDiv | Bin::Mod => {
            if b == 0 {
                return Err(err("divisione per zero"));
            }
            let q = a
                .checked_div_euclid(b)
                .ok_or_else(|| err("numero troppo grande"))?;
            let r = a
                .checked_rem_euclid(b)
                .ok_or_else(|| err("numero troppo grande"))?;
            let (q, r) = if b < 0 && r != 0 {
                (q.checked_sub(1).unwrap_or(q), r.checked_add(b).unwrap_or(r))
            } else {
                (q, r)
            };
            Value::Int(if op == Bin::Mod { r } else { q })
        }
        Bin::Pow => {
            let exp = b.min(MAX_EXP);
            if exp < 0 {
                if a == 0 {
                    return Err(err("divisione per zero"));
                }
                Value::Float(fa.powf(exp as f64))
            } else {
                let e = u32::try_from(exp).unwrap_or(0);
                int_or_float(a.checked_pow(e), || fa.powf(exp as f64))
            }
        }
        Bin::Other => return Err(err("costrutto non permesso: BinOp")),
    })
}

fn arith_float(op: Bin, a: f64, b: f64) -> Result<Value, Fault> {
    let out = match op {
        Bin::Add => a + b,
        Bin::Sub => a - b,
        Bin::Mul => a * b,
        Bin::Div => {
            if b == 0.0 {
                return Err(err("divisione per zero"));
            }
            a / b
        }
        Bin::FloorDiv | Bin::Mod => {
            if b == 0.0 {
                return Err(err("divisione per zero"));
            }
            let m = a % b;
            let m = if m != 0.0 && (m < 0.0) != (b < 0.0) {
                m + b
            } else {
                m
            };
            if op == Bin::Mod {
                if m == 0.0 { 0.0_f64.copysign(b) } else { m }
            } else {
                ((a - m) / b).round()
            }
        }
        Bin::Pow => {
            let exp = b.min(64.0);
            if a == 0.0 && exp < 0.0 {
                return Err(err("divisione per zero"));
            }
            if a < 0.0 && exp.fract() != 0.0 {
                return Err(err("risultato complesso non supportato"));
            }
            let out = a.powf(exp);
            if out.is_infinite() && a.is_finite() {
                return Err(err("numero troppo grande"));
            }
            out
        }
        Bin::Other => return Err(err("costrutto non permesso: BinOp")),
    };
    Ok(Value::Float(out))
}

pub fn binary(op: Bin, left: Value, right: Value) -> Result<Value, Fault> {
    if op == Bin::Other {
        return Err(err("costrutto non permesso: BinOp"));
    }
    if op == Bin::Add && (matches!(left, Value::Str(_)) || matches!(right, Value::Str(_))) {
        let text = format!("{}{}", left.py_str(), right.py_str());
        if text.len() > MAX_TEXT {
            return Err(err("risultato troppo grande"));
        }
        return Ok(Value::Str(text));
    }
    let left_ok = left.is_numeric() || matches!(left, Value::List(_));
    let (left, right) = if !left_ok || !right.is_numeric() {
        (
            Value::Float(number(&left, 0.0)),
            Value::Float(number(&right, 0.0)),
        )
    } else {
        (left, right)
    };
    if let Value::List(items) = &left {
        let count = right
            .as_int()
            .ok_or_else(|| err("operazione non valida su una lista"))?;
        if op != Bin::Mul {
            return Err(err("operazione non valida su una lista"));
        }
        let times = usize::try_from(count.max(0)).map_err(|_| err("risultato troppo grande"))?;
        checked_len(items.len().saturating_mul(times))?;
        let mut out = Vec::with_capacity(items.len().saturating_mul(times));
        for _ in 0..times {
            out.extend(items.iter().cloned());
        }
        return Ok(Value::List(out));
    }
    match (left.as_int(), right.as_int()) {
        (Some(a), Some(b)) => arith_int(op, a, b),
        _ => arith_float(
            op,
            left.as_f64().unwrap_or(0.0),
            right.as_f64().unwrap_or(0.0),
        ),
    }
}

fn order(op: Cmp, a: &Value, b: &Value) -> bool {
    if let (Value::Str(x), Value::Str(y)) = (a, b) {
        return match op {
            Cmp::Lt => x < y,
            Cmp::LtE => x <= y,
            Cmp::Gt => x > y,
            _ => x >= y,
        };
    }
    let (x, y) = (number(a, 0.0), number(b, 0.0));
    match op {
        Cmp::Lt => x < y,
        Cmp::LtE => x <= y,
        Cmp::Gt => x > y,
        _ => x >= y,
    }
}

fn contains(item: &Value, container: &Value) -> Result<bool, Fault> {
    match container {
        Value::Str(s) => match item {
            Value::Str(i) => Ok(s.contains(i.as_str())),
            _ => Err(err("confronto 'in' non valido")),
        },
        Value::List(items) => Ok(items.iter().any(|x| x.py_eq(item))),
        Value::Map(pairs) => {
            if !item.hashable() {
                return Err(err("chiave non valida"));
            }
            Ok(lookup(pairs, item).is_some())
        }
        _ => Err(err("confronto 'in' non valido")),
    }
}

fn compare(op: Cmp, a: &Value, b: &Value) -> Result<bool, Fault> {
    match op {
        Cmp::Eq => Ok(a.py_eq(b)),
        Cmp::NotEq => Ok(!a.py_eq(b)),
        Cmp::Lt | Cmp::LtE | Cmp::Gt | Cmp::GtE => Ok(order(op, a, b)),
        Cmp::In => contains(a, b),
        Cmp::NotIn => contains(a, b).map(|v| !v),
        Cmp::Is | Cmp::IsNot => Ok(false),
    }
}

fn index(base: &Value, key: &Value) -> Value {
    match base {
        Value::List(items) => key
            .as_int()
            .and_then(|i| {
                let len = i128::try_from(items.len()).ok()?;
                let at = if i < 0 { i.checked_add(len)? } else { i };
                items.get(usize::try_from(at).ok()?).cloned()
            })
            .unwrap_or(Value::Null),
        Value::Str(s) => key
            .as_int()
            .and_then(|i| {
                let count = i128::try_from(s.chars().count()).ok()?;
                let at = if i < 0 { i.checked_add(count)? } else { i };
                s.chars()
                    .nth(usize::try_from(at).ok()?)
                    .map(|c| Value::Str(c.to_string()))
            })
            .unwrap_or(Value::Null),
        Value::Map(pairs) if key.hashable() => lookup(pairs, key).cloned().unwrap_or(Value::Null),
        _ => Value::Null,
    }
}

impl<'h, H: Host> Evaluator<'h, H> {
    pub fn new(host: &'h mut H) -> Self {
        Self { host, steps: 0 }
    }

    #[allow(clippy::too_many_lines)]
    pub fn eval(&mut self, n: &Node) -> Result<Value, Fault> {
        self.steps = self.steps.saturating_add(1);
        if self.steps > MAX_STEPS {
            return Err(err("espressione troppo complessa"));
        }
        match n {
            Node::Int(i) => Ok(Value::Int(*i)),
            Node::Float(f) => Ok(Value::Float(*f)),
            Node::Str(s) => Ok(Value::Str(s.clone())),
            Node::Bool(b) => Ok(Value::Bool(*b)),
            Node::Null => Ok(Value::Null),
            Node::Name(name) => Ok(match name.as_str() {
                "true" | "vero" => Value::Bool(true),
                "false" | "falso" => Value::Bool(false),
                "none" | "null" => Value::Null,
                _ => self.host.name(name)?.unwrap_or(Value::Null),
            }),
            Node::And(items) => {
                let mut out = Value::Bool(true);
                for item in items {
                    out = self.eval(item)?;
                    if !out.truthy() {
                        return Ok(out);
                    }
                }
                Ok(out)
            }
            Node::Or(items) => {
                let mut out = Value::Bool(false);
                for item in items {
                    out = self.eval(item)?;
                    if out.truthy() {
                        return Ok(out);
                    }
                }
                Ok(out)
            }
            Node::Binary(op, l, r) => {
                if *op == Bin::Other {
                    return Err(err("costrutto non permesso: BinOp"));
                }
                let left = self.eval(l)?;
                let right = self.eval(r)?;
                binary(*op, left, right)
            }
            Node::Unary(op, inner) => self.unary(*op, inner),
            Node::Compare(first, rest) => {
                let mut left = self.eval(first)?;
                for (op, node) in rest {
                    let right = self.eval(node)?;
                    if !compare(*op, &left, &right)? {
                        return Ok(Value::Bool(false));
                    }
                    left = right;
                }
                Ok(Value::Bool(true))
            }
            Node::IfExp(cond, body, other) => {
                if self.eval(cond)?.truthy() {
                    self.eval(body)
                } else {
                    self.eval(other)
                }
            }
            Node::Attr(base, attr) => match self.eval(base)? {
                Value::Map(pairs) => Ok(lookup(&pairs, &Value::Str(attr.clone()))
                    .cloned()
                    .unwrap_or(Value::Null)),
                _ => Err(err(format!("attributo non accessibile: {attr}"))),
            },
            Node::Index(base, key) => {
                let b = self.eval(base)?;
                let k = self.eval(key)?;
                Ok(index(&b, &k))
            }
            Node::List(items) => {
                checked_len(items.len())?;
                items
                    .iter()
                    .map(|x| self.eval(x))
                    .collect::<Result<Vec<_>, _>>()
                    .map(Value::List)
            }
            Node::Dict(pairs) => {
                let mut out = Vec::with_capacity(pairs.len());
                for (k, v) in pairs {
                    let key = self.eval(k)?;
                    let value = self.eval(v)?;
                    if !key.hashable() {
                        return Err(err("chiave non valida"));
                    }
                    insert(&mut out, key, value);
                }
                Ok(Value::Map(out))
            }
            Node::Call(name, args) => {
                if !matches!(self.host.name(name)?, Some(Value::Func(_))) {
                    return Err(err(format!("funzione sconosciuta: {name}")));
                }
                let values = args
                    .iter()
                    .map(|a| self.eval(a))
                    .collect::<Result<Vec<_>, _>>()?;
                match builtins::call(name, &values) {
                    Some(result) => result,
                    None => self.host.call(name, values),
                }
            }
            Node::Denied(what) => Err(err(format!("costrutto non permesso: {what}"))),
        }
    }

    fn unary(&mut self, op: Unary, inner: &Node) -> Result<Value, Fault> {
        if op == Unary::Invert {
            return Err(err("costrutto non permesso: UnaryOp"));
        }
        let value = self.eval(inner)?;
        match op {
            Unary::Not => Ok(Value::Bool(!value.truthy())),
            Unary::Neg => match value {
                Value::Bool(_) | Value::Int(_) => value
                    .as_int()
                    .and_then(i128::checked_neg)
                    .map(Value::Int)
                    .ok_or_else(|| err("numero troppo grande")),
                Value::Float(f) => Ok(Value::Float(-f)),
                _ => Err(err("segno non valido")),
            },
            Unary::Pos => match value {
                Value::Bool(_) | Value::Int(_) => Ok(Value::Int(value.as_int().unwrap_or(0))),
                Value::Float(_) => Ok(value),
                _ => Err(err("segno non valido")),
            },
            Unary::Invert => Err(err("costrutto non permesso: UnaryOp")),
        }
    }
}
