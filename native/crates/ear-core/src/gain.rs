const A_SMALL: [f32; 6] = [
    -0.577_215_7,
    0.999_991_9,
    -0.249_910_5,
    0.055_199_68,
    -0.009_760_04,
    0.001_078_57,
];
const A1: f32 = 2.334_733;
const A2: f32 = 0.250_621;
const B1: f32 = 3.330_657;
const B2: f32 = 1.681_534;
const V_MIN: f32 = 1e-6;
const V_MAX: f32 = 80.0;

#[must_use]
pub fn exp_integral(x: f32) -> f32 {
    let x = x.clamp(V_MIN, V_MAX);
    if x < 1.0 {
        let poly = A_SMALL.iter().rev().fold(0.0_f32, |acc, a| acc * x + a);
        poly - x.ln()
    } else {
        let ratio = (x * x + A1 * x + A2) / (x * x + B1 * x + B2);
        ratio * (-x).exp() / x
    }
}

#[must_use]
pub fn omlsa_gain(xi: f32, gamma: f32, absence: f32, floor: f32) -> f32 {
    let xi = xi.max(0.0);
    let ratio = xi / (1.0 + xi);
    let v = (ratio * gamma).clamp(V_MIN, V_MAX);
    let present = (ratio * (0.5 * exp_integral(v)).exp()).clamp(0.0, 1.0);
    let q = absence.clamp(0.02, 0.98);
    let odds = q / (1.0 - q) * (1.0 + xi) * (-v).exp();
    let p = 1.0 / (1.0 + odds);
    let floor = floor.clamp(1e-3, 1.0);
    (present.max(floor).powf(p) * floor.powf(1.0 - p)).clamp(floor, 1.0)
}
