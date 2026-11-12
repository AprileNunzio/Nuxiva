#![allow(clippy::many_single_char_names)]

use crate::anatomy::Cleaned;
use crate::plan::{Axis, Node, PathKind, Shape};

pub(crate) type V = [f64; 3];

pub(crate) fn seg(a: V, b: V, r0: f64, r1: f64, color: usize, weight: f64) -> Node {
    let ([ax, ay, az], [bx, by, bz]) = (a, b);
    let dir = [bx - ax, by - ay, bz - az];
    let length = (dir.iter().map(|v| v * v).sum::<f64>()).sqrt().max(1e-3);
    Node::Sweep {
        path: PathKind::Line,
        from: a,
        dir,
        length,
        bend: 0.0,
        r0,
        r1,
        steps: 1,
        color,
        weight,
    }
}

pub(crate) struct Curve {
    pub(crate) from: V,
    pub(crate) dir: V,
    pub(crate) length: f64,
    pub(crate) bend: f64,
    pub(crate) r0: f64,
    pub(crate) r1: f64,
    pub(crate) steps: usize,
    pub(crate) color: usize,
}

pub(crate) fn curve(c: &Curve) -> Node {
    Node::Sweep {
        path: PathKind::Arc,
        from: c.from,
        dir: c.dir,
        length: c.length.max(1e-3),
        bend: c.bend,
        r0: c.r0,
        r1: c.r1,
        steps: c.steps,
        color: c.color,
        weight: 1.2,
    }
}

pub(crate) fn blob(shape: Shape, at: V, size: V, color: usize, weight: f64) -> Node {
    Node::Blob {
        shape,
        at,
        size,
        rot: [0.0; 3],
        color,
        weight,
    }
}

pub(crate) fn tilted(shape: Shape, at: V, size: V, rot: V, color: usize) -> Node {
    Node::Blob {
        shape,
        at,
        size,
        rot,
        color,
        weight: 1.2,
    }
}

pub(crate) fn mark(name: &str, at: V) -> Node {
    Node::Mark {
        name: name.to_owned(),
        at,
    }
}

pub(crate) fn mir(child: Node) -> Node {
    Node::Mirror {
        axis: Axis::X,
        child: Box::new(child),
    }
}

pub(crate) fn group(children: Vec<Node>) -> Node {
    Node::Group { children }
}

pub(crate) fn lying(profile: Vec<[f64; 2]>, weight: f64) -> Node {
    Node::Rotate {
        axis: Axis::X,
        deg: 90.0,
        child: Box::new(Node::Lathe {
            profile,
            color: 0,
            weight,
        }),
    }
}

pub(crate) fn body_profile(length: f64, radius: f64, front: f64) -> Vec<[f64; 2]> {
    (0..15)
        .map(|i| {
            let t = f64::from(i) / 14.0;
            let swell = (std::f64::consts::PI * (0.07 + 0.86 * t)).sin().powf(0.7);
            let bias = 1.0 + front * (t - 0.5);
            [radius * swell * bias, length * (t - 0.5)]
        })
        .collect()
}

pub(crate) fn limb(hip: V, knee: V, foot: V, thick: f64) -> Node {
    let ([fx, fy, fz], t) = (foot, thick);
    group(vec![
        seg(hip, knee, t * 1.25, t * 0.85, 0, 1.3),
        seg(knee, foot, t * 0.8, t * 0.55, 0, 1.2),
        blob(
            Shape::Sphere,
            [fx, fy - t * 0.2, fz + t * 0.3],
            [t * 0.7, t * 0.45, t * 0.95],
            1,
            1.4,
        ),
    ])
}

fn ear(p: &Cleaned, hs: f64, c: V) -> Option<Node> {
    let [x, y, z] = c;
    let es = p.ear_size;
    let side = [x + hs * 0.5, y + hs * 0.7, z - hs * 0.1];
    let shape = match p.ears.as_str() {
        "point" => tilted(
            Shape::Cone,
            [side[0], side[1] + hs * 0.3 * es, side[2]],
            [hs * 0.34 * es, hs * 0.75 * es, hs * 0.14],
            [0.0, 0.0, 0.0],
            1,
        ),
        "round" => blob(
            Shape::Sphere,
            side,
            [hs * 0.34 * es, hs * 0.38 * es, hs * 0.1],
            1,
            1.4,
        ),
        "floppy" => curve(&Curve {
            from: [side[0], side[1] - hs * 0.1, side[2]],
            dir: [0.6, -0.7, -0.2],
            length: hs * 0.95 * es,
            bend: 0.5,
            r0: hs * 0.2,
            r1: hs * 0.13,
            steps: 2,
            color: 1,
        }),
        "long" => curve(&Curve {
            from: [x + hs * 0.25, y + hs * 0.7, z - hs * 0.2],
            dir: [0.2, 1.0, -0.2],
            length: hs * 1.7 * es,
            bend: -0.2,
            r0: hs * 0.2,
            r1: hs * 0.07,
            steps: 2,
            color: 1,
        }),
        _ => return None,
    };
    Some(mir(shape))
}

pub(crate) fn head(p: &Cleaned, hs: f64, c: V, beak: bool) -> Vec<Node> {
    let [x, y, z] = c;
    let mut out = vec![blob(
        Shape::Sphere,
        c,
        [hs * 0.9, hs * 0.85, hs * 1.05],
        0,
        1.8,
    )];
    if p.snout > 0.05 {
        let end = z + hs * 0.7 + hs * p.snout * 1.1;
        let (r0, r1, color) = if beak {
            (hs * 0.4, hs * 0.04, 3)
        } else {
            (hs * 0.5, hs * 0.38, 0)
        };
        out.push(seg(
            [x, y - hs * 0.2, z + hs * 0.6],
            [x, y - hs * 0.3, end],
            r0,
            r1,
            color,
            1.3,
        ));
        if !beak {
            out.push(blob(
                Shape::Sphere,
                [x, y - hs * 0.28, end + hs * 0.05],
                [hs * 0.15; 3],
                5,
                2.2,
            ));
        }
    }
    out.push(mir(blob(
        Shape::Sphere,
        [x + hs * 0.45, y + hs * 0.25, z + hs * 0.5],
        [hs * 0.13; 3],
        4,
        3.0,
    )));
    out.push(mark("head", c));
    out.push(mark(
        if beak { "beak" } else { "snout" },
        [x, y - hs * 0.3, z + hs * 0.7 + hs * p.snout * 0.6],
    ));
    if p.ears != "none" {
        out.push(mark("ears", [x + hs * 0.5, y + hs * 0.9, z - hs * 0.1]));
    }
    out.extend(ear(p, hs, c));
    if p.horns > 0.05 {
        out.push(mark("horns", [x + hs * 0.5, y + hs * 1.5, z - hs * 0.2]));
        out.push(mir(curve(&Curve {
            from: [x + hs * 0.3, y + hs * 0.7, z - hs * 0.1],
            dir: [0.5, 1.0, -0.2],
            length: hs * p.horns * 1.4,
            bend: 0.7,
            r0: hs * 0.14,
            r1: hs * 0.03,
            steps: 3,
            color: 2,
        })));
    }
    out
}

pub(crate) fn wings(p: &Cleaned, root: V, span: f64) -> Vec<Node> {
    if p.wings < 0.05 {
        return Vec::new();
    }
    let [x, y, z] = root;
    let thick = span * 0.05;
    [
        ([1.0, 0.5, -0.2], 1.0),
        ([1.0, 0.1, -0.45], 0.9),
        ([0.8, -0.25, -0.7], 0.7),
    ]
    .into_iter()
    .map(|(dir, k)| {
        mir(curve(&Curve {
            from: [x, y, z],
            dir,
            length: span * k,
            bend: -0.3,
            r0: thick,
            r1: thick * 0.3,
            steps: 2,
            color: 2,
        }))
    })
    .collect()
}

pub(crate) fn tail(p: &Cleaned, from: V, length: f64, radius: f64) -> Option<Node> {
    (p.tail > 0.05).then(|| {
        curve(&Curve {
            from,
            dir: [0.0, 0.6, -1.0],
            length: length * p.tail,
            bend: p.tail_curl,
            r0: radius,
            r1: radius * 0.25,
            steps: 4,
            color: 2,
        })
    })
}
