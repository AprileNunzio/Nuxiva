use std::f64::consts::TAU;

use crate::plan::{
    Axis, FormaError, MAX_COUNT, MAX_DEPTH, MAX_NODES, MAX_PRIMS, MAX_PROFILE, MAX_STEPS, Node,
    PathKind, Shape,
};

pub(crate) type V = [f64; 3];

const LIMIT: f64 = 100.0;

#[derive(Debug, Clone)]
pub(crate) enum Prim {
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

pub(crate) fn sub(a: V, b: V) -> V {
    let ([ax, ay, az], [bx, by, bz]) = (a, b);
    [ax - bx, ay - by, az - bz]
}

pub(crate) fn add(a: V, b: V) -> V {
    let ([ax, ay, az], [bx, by, bz]) = (a, b);
    [ax + bx, ay + by, az + bz]
}

pub(crate) fn scale(a: V, k: f64) -> V {
    a.map(|v| v * k)
}

pub(crate) fn cross(a: V, b: V) -> V {
    let ([ax, ay, az], [bx, by, bz]) = (a, b);
    [ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx]
}

pub(crate) fn norm(a: V) -> f64 {
    let [x, y, z] = a;
    (x * x + y * y + z * z).sqrt()
}

pub(crate) fn unit(a: V) -> Option<V> {
    let n = norm(a);
    (n > 1e-9).then(|| scale(a, 1.0 / n))
}

pub(crate) fn finite(values: &[f64]) -> Result<(), FormaError> {
    if values.iter().all(|v| v.is_finite() && v.abs() <= LIMIT) {
        Ok(())
    } else {
        Err(FormaError("out_of_range"))
    }
}

pub(crate) fn rotate(p: V, axis: Axis, deg: f64) -> V {
    let (sin, cos) = deg.to_radians().sin_cos();
    let [x, y, z] = p;
    match axis {
        Axis::X => [x, y * cos - z * sin, y * sin + z * cos],
        Axis::Y => [x * cos + z * sin, y, -x * sin + z * cos],
        Axis::Z => [x * cos - y * sin, x * sin + y * cos, z],
    }
}

pub(crate) fn mirror(p: V, axis: Axis) -> V {
    let [x, y, z] = p;
    match axis {
        Axis::X => [-x, y, z],
        Axis::Y => [x, -y, z],
        Axis::Z => [x, y, -z],
    }
}

pub(crate) fn map_prim(prim: &Prim, f: &dyn Fn(V) -> V, yaw: f64) -> Prim {
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

pub(crate) struct Builder {
    pub(crate) nodes: usize,
    pub(crate) out: Vec<Prim>,
}

impl Builder {
    pub(crate) fn room(&self, extra: usize) -> Result<(), FormaError> {
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

    pub(crate) fn emit(&mut self, node: &Node, depth: usize) -> Result<(), FormaError> {
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

pub(crate) struct Sweep {
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
