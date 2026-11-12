use serde::Serialize;
use std::f64::consts::TAU;

use crate::plan::{
    Axis, FormaError, MAX_COUNT, MAX_DEPTH, MAX_NODES, MAX_PARTS, MAX_PRIMS, MAX_PROFILE,
    MAX_STEPS, Node, PathKind, Plan, Shape,
};

type V = [f64; 3];

const REACH: f64 = 3.0;
const LIMIT: f64 = 100.0;

#[derive(Debug, Clone, Serialize)]
pub struct Part {
    pub shape: Shape,
    pub size: V,
    pub at: V,
    pub rot: V,
    pub color: String,
    pub weight: f64,
}

#[derive(Debug, Clone)]
enum Prim {
    Seg {
        a: V,
        b: V,
        r0: f64,
        r1: f64,
        color: usize,
        weight: f64,
    },
    Blob {
        shape: Shape,
        at: V,
        size: V,
        rot: V,
        color: usize,
        weight: f64,
    },
}

#[must_use]
pub fn palette(theme: &str) -> [&'static str; 6] {
    match theme {
        "bioluminescent" => [
            "#4ce6ff", "#7952ec", "#a87bff", "#ff6be5", "#5ef2ff", "#c49bff",
        ],
        "celestial" => [
            "#ffd166", "#5ce1e6", "#480ca8", "#72efdd", "#9b7bff", "#ff9f1c",
        ],
        "botanical" => [
            "#38b000", "#70e000", "#a7c957", "#ff70a6", "#ffb703", "#007200",
        ],
        "fauna" => [
            "#ee9b00", "#ca6702", "#bb3e03", "#0077b6", "#90e0ef", "#f1faee",
        ],
        "mechanical" => [
            "#64dfdf", "#48bfe3", "#5390d9", "#ff9f1c", "#80ffdb", "#7400b8",
        ],
        "microscopic" => [
            "#ff006e", "#00f5d4", "#8338ec", "#fee440", "#3a86ff", "#ffbe0b",
        ],
        "geological" => [
            "#2ec4b6", "#e71d36", "#ff9f1c", "#7209b7", "#e0aaff", "#c77dff",
        ],
        _ => [
            "#5ef2ff", "#9b7bff", "#66ffe3", "#ff7be5", "#7aa2ff", "#ffd166",
        ],
    }
}

fn sub(a: V, b: V) -> V {
    let ([ax, ay, az], [bx, by, bz]) = (a, b);
    [ax - bx, ay - by, az - bz]
}

fn add(a: V, b: V) -> V {
    let ([ax, ay, az], [bx, by, bz]) = (a, b);
    [ax + bx, ay + by, az + bz]
}

fn scale(a: V, k: f64) -> V {
    a.map(|v| v * k)
}

fn cross(a: V, b: V) -> V {
    let ([ax, ay, az], [bx, by, bz]) = (a, b);
    [ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx]
}

fn norm(a: V) -> f64 {
    let [x, y, z] = a;
    (x * x + y * y + z * z).sqrt()
}

fn unit(a: V) -> Option<V> {
    let n = norm(a);
    (n > 1e-9).then(|| scale(a, 1.0 / n))
}

fn finite(values: &[f64]) -> Result<(), FormaError> {
    if values.iter().all(|v| v.is_finite() && v.abs() <= LIMIT) {
        Ok(())
    } else {
        Err(FormaError("out_of_range"))
    }
}

fn rotate(p: V, axis: Axis, deg: f64) -> V {
    let (sin, cos) = deg.to_radians().sin_cos();
    let [x, y, z] = p;
    match axis {
        Axis::X => [x, y * cos - z * sin, y * sin + z * cos],
        Axis::Y => [x * cos + z * sin, y, -x * sin + z * cos],
        Axis::Z => [x * cos - y * sin, x * sin + y * cos, z],
    }
}

fn mirror(p: V, axis: Axis) -> V {
    let [x, y, z] = p;
    match axis {
        Axis::X => [-x, y, z],
        Axis::Y => [x, -y, z],
        Axis::Z => [x, y, -z],
    }
}

fn map_prim(prim: &Prim, f: &dyn Fn(V) -> V, yaw: f64) -> Prim {
    match prim {
        Prim::Seg {
            a,
            b,
            r0,
            r1,
            color,
            weight,
        } => Prim::Seg {
            a: f(*a),
            b: f(*b),
            r0: *r0,
            r1: *r1,
            color: *color,
            weight: *weight,
        },
        Prim::Blob {
            shape,
            at,
            size,
            rot,
            color,
            weight,
        } => {
            let [rx, ry, rz] = *rot;
            Prim::Blob {
                shape: *shape,
                at: f(*at),
                size: *size,
                rot: [rx, ry + yaw, rz],
                color: *color,
                weight: *weight,
            }
        }
    }
}

struct Builder {
    nodes: usize,
    out: Vec<Prim>,
}

impl Builder {
    fn room(&self, extra: usize) -> Result<(), FormaError> {
        if self.out.len().saturating_add(extra) > MAX_PRIMS {
            Err(FormaError("too_many_parts"))
        } else {
            Ok(())
        }
    }

    fn child(&mut self, node: &Node, depth: usize) -> Result<Vec<Prim>, FormaError> {
        let outer = std::mem::take(&mut self.out);
        let built = self.emit(node, depth);
        let inner = std::mem::replace(&mut self.out, outer);
        built.map(|()| inner)
    }

    fn emit(&mut self, node: &Node, depth: usize) -> Result<(), FormaError> {
        self.nodes = self.nodes.saturating_add(1);
        if self.nodes > MAX_NODES || depth > MAX_DEPTH {
            return Err(FormaError("too_complex"));
        }
        match node {
            Node::Lathe {
                profile,
                color,
                weight,
            } => self.lathe(profile, *color, *weight),
            Node::Sweep {
                path,
                from,
                dir,
                length,
                bend,
                r0,
                r1,
                steps,
                color,
                weight,
            } => self.sweep(&Sweep {
                path: *path,
                from: *from,
                dir: *dir,
                length: *length,
                bend: *bend,
                r0: *r0,
                r1: *r1,
                steps: *steps,
                color: *color,
                weight: *weight,
            }),
            Node::Blob {
                shape,
                at,
                size,
                rot,
                color,
                weight,
            } => {
                finite(at)?;
                finite(size)?;
                finite(rot)?;
                finite(&[*weight])?;
                self.room(1)?;
                self.out.push(Prim::Blob {
                    shape: *shape,
                    at: *at,
                    size: *size,
                    rot: *rot,
                    color: *color,
                    weight: *weight,
                });
                Ok(())
            }
            Node::Radial {
                count,
                radius,
                phase,
                child,
            } => self.radial(*count, *radius, *phase, child, depth),
            Node::Mirror { axis, child } => self.mirrored(*axis, child, depth),
            Node::Rotate { axis, deg, child } => self.rotated(*axis, *deg, child, depth),
            Node::Group { children } => {
                for node in children {
                    self.emit(node, depth.saturating_add(1))?;
                }
                Ok(())
            }
        }
    }

    fn radial(
        &mut self,
        count: usize,
        radius: f64,
        phase: f64,
        child: &Node,
        depth: usize,
    ) -> Result<(), FormaError> {
        finite(&[radius, phase])?;
        if count == 0 || count > MAX_COUNT {
            return Err(FormaError("bad_count"));
        }
        let inner = self.child(child, depth.saturating_add(1))?;
        self.room(inner.len().saturating_mul(count))?;
        for i in 0..count {
            #[allow(clippy::cast_precision_loss)]
            let angle = phase + 360.0 * i as f64 / count as f64;
            let place = |p: V| rotate(add(p, [radius, 0.0, 0.0]), Axis::Y, angle);
            self.out
                .extend(inner.iter().map(|prim| map_prim(prim, &place, angle)));
        }
        Ok(())
    }

    fn mirrored(&mut self, axis: Axis, child: &Node, depth: usize) -> Result<(), FormaError> {
        let inner = self.child(child, depth.saturating_add(1))?;
        self.room(inner.len().saturating_mul(2))?;
        let flip = |p: V| mirror(p, axis);
        let flipped: Vec<Prim> = inner.iter().map(|p| map_prim(p, &flip, 0.0)).collect();
        self.out.extend(inner);
        self.out.extend(flipped);
        Ok(())
    }

    fn rotated(
        &mut self,
        axis: Axis,
        deg: f64,
        child: &Node,
        depth: usize,
    ) -> Result<(), FormaError> {
        finite(&[deg])?;
        let inner = self.child(child, depth.saturating_add(1))?;
        self.room(inner.len())?;
        let turn = |p: V| rotate(p, axis, deg);
        let yaw = if axis == Axis::Y { deg } else { 0.0 };
        self.out
            .extend(inner.iter().map(|prim| map_prim(prim, &turn, yaw)));
        Ok(())
    }

    fn lathe(&mut self, profile: &[[f64; 2]], color: usize, weight: f64) -> Result<(), FormaError> {
        if profile.len() < 2 || profile.len() > MAX_PROFILE {
            return Err(FormaError("bad_profile"));
        }
        finite(&[weight])?;
        self.room(profile.len())?;
        for pair in profile.windows(2) {
            let (Some([r0, y0]), Some([r1, y1])) = (pair.first().copied(), pair.get(1).copied())
            else {
                continue;
            };
            finite(&[r0, y0, r1, y1])?;
            if r0 < 0.0 || r1 < 0.0 {
                return Err(FormaError("bad_profile"));
            }
            self.out.push(Prim::Seg {
                a: [0.0, y0, 0.0],
                b: [0.0, y1, 0.0],
                r0,
                r1,
                color,
                weight,
            });
        }
        Ok(())
    }

    fn sweep(&mut self, s: &Sweep) -> Result<(), FormaError> {
        finite(&s.from)?;
        finite(&s.dir)?;
        finite(&[s.length, s.bend, s.r0, s.r1, s.weight])?;
        if s.steps == 0 || s.steps > MAX_STEPS || s.r0 < 0.0 || s.r1 < 0.0 {
            return Err(FormaError("bad_sweep"));
        }
        let d = unit(s.dir).ok_or(FormaError("bad_sweep"))?;
        let helper = if d.get(1).is_some_and(|y| y.abs() < 0.9) {
            [0.0, 1.0, 0.0]
        } else {
            [1.0, 0.0, 0.0]
        };
        let u = unit(cross(d, helper)).ok_or(FormaError("bad_sweep"))?;
        let v = cross(d, u);
        self.room(s.steps)?;
        let bend = s.bend.clamp(-2.0, 2.0);
        let at = |t: f64| -> V {
            let off = match s.path {
                PathKind::Line => [0.0; 3],
                PathKind::Arc => scale(u, bend * s.length * t * t * 0.5),
                PathKind::Wave => scale(u, bend * s.length * 0.25 * (TAU * t).sin()),
                PathKind::Spiral => {
                    let theta = TAU * 1.5 * t;
                    let rad = bend.abs() * s.length * 0.3 * t;
                    scale(add(scale(u, theta.cos() - 1.0), scale(v, theta.sin())), rad)
                }
            };
            add(add(s.from, scale(d, s.length * t)), off)
        };
        #[allow(clippy::cast_precision_loss)]
        let total = s.steps as f64;
        for i in 0..s.steps {
            #[allow(clippy::cast_precision_loss)]
            let t0 = i as f64 / total;
            #[allow(clippy::cast_precision_loss)]
            let t1 = (i.saturating_add(1)) as f64 / total;
            self.out.push(Prim::Seg {
                a: at(t0),
                b: at(t1),
                r0: s.r0 + (s.r1 - s.r0) * t0,
                r1: s.r0 + (s.r1 - s.r0) * t1,
                color: s.color,
                weight: s.weight,
            });
        }
        Ok(())
    }
}

struct Sweep {
    path: PathKind,
    from: V,
    dir: V,
    length: f64,
    bend: f64,
    r0: f64,
    r1: f64,
    steps: usize,
    color: usize,
    weight: f64,
}

fn reach(prims: &[Prim]) -> f64 {
    prims
        .iter()
        .map(|p| match p {
            Prim::Seg { a, b, r0, r1, .. } => {
                let extent = |q: &V| q.iter().map(|v| v.abs()).fold(0.0_f64, f64::max);
                extent(a).max(extent(b)) + r0.max(*r1)
            }
            Prim::Blob { at, size, .. } => {
                at.iter().map(|v| v.abs()).fold(0.0_f64, f64::max)
                    + size.iter().copied().fold(0.0_f64, f64::max)
            }
        })
        .fold(0.0_f64, f64::max)
}

fn wrap(deg: f64) -> f64 {
    let m = deg.rem_euclid(360.0);
    if m > 180.0 { m - 360.0 } else { m }
}

fn tint(palette: &[&str; 6], index: usize) -> String {
    palette
        .get(index.checked_rem(6).unwrap_or(0))
        .copied()
        .unwrap_or("#9be7ff")
        .to_owned()
}

fn seg_part(a: V, b: V, r0: f64, r1: f64, k: f64) -> Option<(Shape, V, V, V)> {
    let (wide, narrow, hi, lo) = if r0 >= r1 {
        (a, b, r0, r1)
    } else {
        (b, a, r1, r0)
    };
    let axis = sub(narrow, wide);
    let length = norm(axis);
    if length < 1e-9 {
        return None;
    }
    let [dx, dy, dz] = scale(axis, 1.0 / length);
    let rx = dy.clamp(-1.0, 1.0).acos().to_degrees();
    let ry = dx.atan2(dz).to_degrees();
    let mid = scale(add(wide, narrow), 0.5);
    let (shape, radius) = if hi > 0.0 && lo < 0.25 * hi {
        (Shape::Cone, hi)
    } else {
        (Shape::Cylinder, f64::midpoint(hi, lo))
    };
    let half = (length * 0.5 * k).clamp(0.01, 10.0);
    let r = (radius * k).clamp(0.01, 10.0);
    Some((shape, [r, half, r], scale(mid, k), [rx, ry, 0.0]))
}

pub fn compile(plan: &Plan) -> Result<Vec<Part>, FormaError> {
    let mut builder = Builder {
        nodes: 0,
        out: Vec::new(),
    };
    for node in &plan.nodes {
        builder.emit(node, 0)?;
    }
    let prims = builder.out;
    let extent = reach(&prims);
    if prims.is_empty() || extent <= 1e-9 {
        return Err(FormaError("empty"));
    }
    let k = REACH / extent;
    let colors = palette(&plan.theme);
    let mut parts = Vec::with_capacity(prims.len());
    for prim in &prims {
        match prim {
            Prim::Seg {
                a,
                b,
                r0,
                r1,
                color,
                weight,
            } => {
                if let Some((shape, size, at, rot)) = seg_part(*a, *b, *r0, *r1, k) {
                    parts.push(Part {
                        shape,
                        size,
                        at,
                        rot,
                        color: tint(&colors, *color),
                        weight: weight.clamp(0.05, 10.0),
                    });
                }
            }
            Prim::Blob {
                shape,
                at,
                size,
                rot,
                color,
                weight,
            } => parts.push(Part {
                shape: *shape,
                size: size.map(|v| (v * k).clamp(0.01, 10.0)),
                at: scale(*at, k),
                rot: rot.map(wrap),
                color: tint(&colors, *color),
                weight: weight.clamp(0.05, 10.0),
            }),
        }
    }
    if parts.is_empty() || parts.len() > MAX_PARTS {
        return Err(FormaError("too_many_parts"));
    }
    Ok(parts)
}
