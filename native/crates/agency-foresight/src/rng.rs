use serde::{Deserialize, Serialize};

const GOLDEN: u64 = 0x9E37_79B9_7F4A_7C15;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Rng {
    state: [u64; 4],
}

#[must_use]
pub fn mix(seed: u64) -> u64 {
    let mut z = seed.wrapping_add(GOLDEN);
    z = (z ^ z.wrapping_shr(30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
    z = (z ^ z.wrapping_shr(27)).wrapping_mul(0x94D0_49BB_1331_11EB);
    z ^ z.wrapping_shr(31)
}

impl Rng {
    #[must_use]
    pub fn new(seed: u64) -> Self {
        let a = mix(seed);
        let b = mix(a);
        let c = mix(b);
        let d = mix(c);
        let state = if (a | b | c | d) == 0 {
            [GOLDEN, 1, 2, 3]
        } else {
            [a, b, c, d]
        };
        Self { state }
    }

    pub fn next_u64(&mut self) -> u64 {
        let [s0, s1, s2, s3] = self.state;
        let result = s1.wrapping_mul(5).rotate_left(7).wrapping_mul(9);
        let t = s1.wrapping_shl(17);
        let n2 = s2 ^ s0;
        let n3 = s3 ^ s1;
        let n1 = s1 ^ n2;
        let n0 = s0 ^ n3;
        self.state = [n0, n1, n2 ^ t, n3.rotate_left(45)];
        result
    }

    pub fn unit(&mut self) -> f64 {
        let bits = 0x3FF0_0000_0000_0000_u64 | self.next_u64().wrapping_shr(12);
        f64::from_bits(bits) - 1.0
    }

    pub fn below(&mut self, bound: usize) -> usize {
        let Ok(bound) = u64::try_from(bound) else {
            return 0;
        };
        self.next_u64()
            .checked_rem(bound)
            .and_then(|v| usize::try_from(v).ok())
            .unwrap_or(0)
    }

    pub fn jitter(&mut self, amplitude: f64) -> f64 {
        (self.unit() * 2.0 - 1.0) * amplitude
    }
}
