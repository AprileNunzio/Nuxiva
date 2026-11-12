#![allow(clippy::many_single_char_names)]

use crate::anatomy::Cleaned;
use crate::anatomy_parts::{
    Curve, V, blob, body_profile, curve, head, limb, lying, mark, mir, seg, tail, tilted, wings,
};
use crate::plan::{Node, PathKind, Shape};

pub(crate) fn quadruped(p: &Cleaned) -> Vec<Node> {
    let l = p.size;
    let r = 0.28 * l * p.build;
    let h = 0.45 * l * p.legs;
    let t = 0.09 * l * p.leg_thick;
    let mut n = vec![
        lying(body_profile(l, r, 0.25), 2.2),
        mark("body", [0.0, r * 0.2, 0.0]),
        mark("front_legs", [r * 0.55, -r * 0.1 - h * 0.5, l * 0.3]),
        mark("hind_legs", [r * 0.55, -h * 0.45, -l * 0.3]),
    ];
    let reach = p.neck * l;
    let base: V = [0.0, r * 0.45, l * 0.40];
    let top: V = [0.0, r * 0.45 + reach * 0.28, l * 0.40 + reach * 0.22];
    if p.neck > 0.05 {
        n.push(seg(base, top, r * 0.55, r * 0.4, 0, 1.4));
        n.push(mark(
            "neck",
            [r * 0.4, r * 0.45 + reach * 0.14, l * 0.4 + reach * 0.11],
        ));
    }
    let hs = p.head * 0.17 * l;
    let [tx, ty, tz] = top;
    n.extend(head(p, hs, [tx, ty + hs * 0.15, tz + hs * 0.7], false));
    let (fz, bz) = (l * 0.32, -l * 0.34);
    n.push(mir(limb(
        [r * 0.55, -r * 0.1, fz],
        [r * 0.55, -r * 0.1 - h * 0.5, fz - l * 0.04],
        [r * 0.52, -r * 0.1 - h, fz + l * 0.02],
        t,
    )));
    n.push(mir(limb(
        [r * 0.55, r * 0.05, bz],
        [r * 0.55, -h * 0.45, bz + l * 0.1],
        [r * 0.5, -h - r * 0.1, bz - l * 0.06],
        t,
    )));
    n.extend(tail(p, [0.0, r * 0.35, -l * 0.5], l * 0.45, r * 0.22));
    if p.tail > 0.05 {
        let len = l * 0.45 * p.tail;
        n.push(mark(
            "tail",
            [0.0, r * 0.35 + len * 0.3, -l * 0.5 - len * 0.5],
        ));
    }
    n.extend(wings(p, [r * 0.4, r * 0.8, l * 0.15], p.wings * l * 0.7));
    if p.wings > 0.05 {
        n.push(mark(
            "wings",
            [
                r * 0.4 + p.wings * l * 0.4,
                r * 0.8 + p.wings * l * 0.2,
                l * 0.1,
            ],
        ));
    }
    n
}

pub(crate) fn biped(p: &Cleaned) -> Vec<Node> {
    let h = p.size;
    let r = 0.16 * h * p.build;
    let t = 0.045 * h * p.leg_thick;
    let leg = 0.45 * h * p.legs;
    let arm = 0.38 * h * p.arms;
    let profile: Vec<[f64; 2]> = (0..8)
        .map(|i| {
            let k = f64::from(i) / 7.0;
            let swell = 0.78 + 0.22 * (std::f64::consts::PI * k.powf(0.8)).sin();
            [r * swell, h * (0.2 * k - 0.18 * (1.0 - k))]
        })
        .collect();
    let mut n = vec![
        Node::Lathe {
            profile,
            color: 0,
            weight: 2.2,
        },
        mark("body", [0.0, 0.02 * h, r]),
        mark("legs", [r * 0.6, -0.18 * h - leg * 0.5, 0.0]),
        mark("arms", [r * 1.2, 0.17 * h - arm * 0.5, 0.0]),
    ];
    let neck = p.neck * 0.08 * h;
    let hs = p.head * 0.09 * h;
    n.push(seg(
        [0.0, 0.2 * h, 0.0],
        [0.0, 0.2 * h + neck + hs * 0.2, 0.01 * h],
        r * 0.3,
        r * 0.27,
        0,
        1.3,
    ));
    n.extend(head(p, hs, [0.0, 0.2 * h + neck + hs, 0.01 * h], false));
    let hip = -0.18 * h;
    n.push(mir(limb(
        [r * 0.45, hip, 0.0],
        [r * 0.45, hip - leg * 0.5, 0.03 * h],
        [r * 0.45, hip - leg, 0.0],
        t,
    )));
    let shoulder = 0.17 * h;
    n.push(mir(limb(
        [r * 0.95, shoulder, 0.0],
        [r * 1.15, shoulder - arm * 0.5, 0.02 * h],
        [r * 1.2, shoulder - arm, 0.05 * h],
        t * 0.8,
    )));
    n.extend(tail(p, [0.0, hip, -r * 0.7], h * 0.3, r * 0.2));
    if p.tail > 0.05 {
        n.push(mark("tail", [0.0, hip + h * 0.1, -r * 0.7 - h * 0.15]));
    }
    n.extend(wings(p, [r * 0.5, 0.15 * h, -r * 0.4], p.wings * h * 0.6));
    if p.wings > 0.05 {
        n.push(mark(
            "wings",
            [r * 0.5 + p.wings * h * 0.3, 0.2 * h, -r * 0.4],
        ));
    }
    n
}

pub(crate) fn bird(p: &Cleaned) -> Vec<Node> {
    let l = p.size;
    let r = 0.22 * l * p.build;
    let mut n = vec![
        lying(body_profile(l, r, 0.3), 2.2),
        mark("body", [0.0, r * 0.2, 0.0]),
        mark("legs", [r * 0.35, -r * 0.6 - 0.35 * l * p.legs * 0.5, 0.0]),
    ];
    let reach = p.neck * l;
    let top: V = [0.0, r * 0.6 + reach * 0.3, l * 0.35 + reach * 0.15];
    n.push(seg([0.0, r * 0.3, l * 0.3], top, r * 0.5, r * 0.35, 0, 1.4));
    let hs = p.head * 0.12 * l;
    let [tx, ty, tz] = top;
    n.extend(head(p, hs, [tx, ty + hs * 0.2, tz + hs * 0.4], true));
    n.extend(wings(p, [r * 0.5, r * 0.5, l * 0.15], p.wings * l * 0.9));
    if p.wings > 0.05 {
        n.push(mark(
            "wings",
            [r * 0.5 + p.wings * l * 0.45, r * 0.6, l * 0.1],
        ));
    }
    if p.tail > 0.05 {
        n.push(mark("tail", [0.0, 0.0, -l * 0.45 - l * 0.2 * p.tail]));
        let reach = l * 0.4 * p.tail;
        for dir in [[0.0, -0.1, -1.0], [0.35, -0.1, -1.0]] {
            let node = seg(
                [0.0, 0.0, -l * 0.45],
                [dir[0] * reach, dir[1] * reach, -l * 0.45 + dir[2] * reach],
                r * 0.35,
                r * 0.06,
                2,
                1.2,
            );
            n.push(if dir[0] > 0.0 { mir(node) } else { node });
        }
    }
    let h = 0.35 * l * p.legs;
    n.push(mir(limb(
        [r * 0.35, -r * 0.6, -l * 0.02],
        [r * 0.35, -r * 0.6 - h * 0.5, l * 0.02],
        [r * 0.35, -r * 0.6 - h, 0.0],
        0.03 * l * p.leg_thick,
    )));
    n
}

pub(crate) fn fish(p: &Cleaned) -> Vec<Node> {
    let l = p.size;
    let r = 0.2 * l * p.build;
    let mut n = vec![
        lying(body_profile(l, r, 0.6), 2.2),
        mark("body", [r * 0.5, 0.0, 0.0]),
        mark(
            "tail",
            [0.0, l * 0.12 * p.tail, -l * 0.46 - l * 0.15 * p.tail],
        ),
    ];
    n.push(mir(blob(
        Shape::Sphere,
        [r * 0.62, r * 0.25, l * 0.33],
        [r * 0.14; 3],
        4,
        3.0,
    )));
    let fin = l * 0.22 * p.tail;
    for k in [1.0, -1.0] {
        n.push(seg(
            [0.0, 0.0, -l * 0.46],
            [0.0, k * fin, -l * 0.46 - fin * 0.8],
            r * 0.22,
            r * 0.03,
            2,
            1.2,
        ));
    }
    if p.wings > 0.05 {
        let up = l * 0.2 * p.wings;
        n.push(mark("fins", [0.0, r * 0.85 + up * 0.6, -l * 0.05]));
        n.push(seg(
            [0.0, r * 0.85, l * 0.05],
            [0.0, r * 0.85 + up, -l * 0.12],
            r * 0.22,
            r * 0.02,
            2,
            1.2,
        ));
        n.push(mir(seg(
            [r * 0.7, -r * 0.2, l * 0.15],
            [r * 0.7 + up * 0.8, -r * 0.2 - up * 0.5, -l * 0.02],
            r * 0.16,
            r * 0.02,
            2,
            1.1,
        )));
    }
    n
}

pub(crate) fn insect(p: &Cleaned) -> Vec<Node> {
    let l = p.size;
    let r = 0.14 * l * p.build;
    let hs = p.head * 0.1 * l;
    let mut n = vec![
        blob(
            Shape::Sphere,
            [0.0, 0.0, l * 0.42],
            [hs * 0.9, hs * 0.85, hs],
            0,
            1.8,
        ),
        blob(
            Shape::Sphere,
            [0.0, 0.0, l * 0.18],
            [r * 0.9, r * 0.85, l * 0.14],
            0,
            2.0,
        ),
        blob(
            Shape::Sphere,
            [0.0, 0.0, -l * 0.22],
            [r * 0.85, r * 0.8, l * 0.3],
            1,
            2.0,
        ),
        mir(blob(
            Shape::Sphere,
            [hs * 0.5, hs * 0.25, l * 0.42 + hs * 0.6],
            [hs * 0.22; 3],
            4,
            3.0,
        )),
        mark("head", [0.0, hs, l * 0.42]),
        mark("thorax", [0.0, r, l * 0.18]),
        mark("abdomen", [0.0, r, -l * 0.22]),
        mark("legs", [r * 1.8, -r * 0.2, l * 0.1]),
    ];
    let pairs = p.pairs.clamp(1, 6);
    for k in 0..pairs {
        let z = l * 0.2 - l * 0.12 * f64::from(k);
        n.push(mir(group_leg(z, r, p.legs, p.leg_thick, l)));
    }
    if p.horns > 0.05 {
        n.push(mir(curve(&Curve {
            from: [hs * 0.3, hs * 0.5, l * 0.42 + hs * 0.6],
            dir: [0.4, 1.0, 0.7],
            length: hs * p.horns * 2.0,
            bend: 0.6,
            r0: hs * 0.07,
            r1: hs * 0.02,
            steps: 2,
            color: 2,
        })));
    }
    if p.wings > 0.05 {
        let w = p.wings * l * 0.45;
        n.push(mark("wings", [w * 0.9, r * 0.9, l * 0.1]));
        n.push(mir(tilted(
            Shape::Plane,
            [w * 0.62, r * 0.9, l * 0.12],
            [w * 0.6, 0.01, l * 0.2],
            [0.0, 0.0, -14.0],
            3,
        )));
        n.push(mir(tilted(
            Shape::Plane,
            [w * 0.5, r * 0.8, -l * 0.1],
            [w * 0.45, 0.01, l * 0.14],
            [0.0, 0.0, -8.0],
            5,
        )));
    }
    n
}

fn group_leg(z: f64, r: f64, legs: f64, thick: f64, l: f64) -> Node {
    let t = 0.012 * l * thick;
    crate::anatomy_parts::group(vec![
        seg(
            [r * 0.6, 0.0, z],
            [r * 1.6, r * 0.9 * legs, z + l * 0.04],
            t * 1.3,
            t,
            0,
            1.2,
        ),
        seg(
            [r * 1.6, r * 0.9 * legs, z + l * 0.04],
            [r * 2.4 * legs, -r * 1.3 * legs, z + l * 0.07],
            t,
            t * 0.5,
            0,
            1.2,
        ),
    ])
}

pub(crate) fn serpent(p: &Cleaned) -> Vec<Node> {
    let l = p.size;
    let r = 0.07 * l * p.build;
    let hs = p.head * 0.06 * l;
    let end = l * 0.5;
    vec![
        Node::Sweep {
            path: PathKind::Wave,
            from: [0.0, 0.0, -end],
            dir: [0.0, 0.0, 1.0],
            length: l,
            bend: p.tail_curl.abs().clamp(0.3, 0.8),
            r0: r * 0.1,
            r1: r,
            steps: 12,
            color: 0,
            weight: 2.0,
        },
        blob(
            Shape::Sphere,
            [0.0, 0.0, end + hs * 0.6],
            [hs * 0.9, hs * 0.7, hs * 1.3],
            1,
            2.0,
        ),
        mir(blob(
            Shape::Sphere,
            [hs * 0.55, hs * 0.25, end + hs * 0.8],
            [hs * 0.15; 3],
            4,
            3.0,
        )),
        mark("head", [0.0, hs, end + hs * 0.6]),
        mark("body", [0.0, r * 1.2, 0.0]),
        mark("tail", [0.0, r * 0.5, -end]),
    ]
}
