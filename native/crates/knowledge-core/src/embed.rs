use sha2::{Digest, Sha256};

use crate::text::tokens;

pub const DIM: usize = 256;
const WORD: i32 = 10;
const GRAM: i32 = 4;
const PAIR: i32 = 6;

#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Vector {
    cells: Vec<(u16, i32)>,
    norm2: i64,
}

fn feature(text: &str) -> (usize, i32) {
    let digest = Sha256::digest(text.as_bytes());
    let mut bytes = [0_u8; 8];
    bytes.copy_from_slice(digest.get(..8).unwrap_or(&[0; 8]));
    let hash = u64::from_be_bytes(bytes);
    let index = usize::try_from(hash.checked_rem(DIM as u64).unwrap_or(0)).unwrap_or(0);
    let sign = if (hash >> 32) & 1 == 1 { -1 } else { 1 };
    (index, sign)
}

fn add(cells: &mut [i32], text: &str, weight: i32) {
    let (index, sign) = feature(text);
    if let Some(cell) = cells.get_mut(index) {
        *cell = cell.saturating_add(sign.saturating_mul(weight));
    }
}

#[must_use]
pub fn embed(text: &str) -> Vector {
    let words = tokens(text);
    let mut cells = vec![0_i32; DIM];
    for word in &words {
        add(&mut cells, &format!("w:{word}"), WORD);
        let padded: Vec<char> = format!("^{word}$").chars().collect();
        for gram in padded.windows(3) {
            add(
                &mut cells,
                &format!("g:{}", gram.iter().collect::<String>()),
                GRAM,
            );
        }
    }
    for pair in words.windows(2) {
        if let [a, b] = pair {
            add(&mut cells, &format!("b:{a} {b}"), PAIR);
        }
    }
    let cells: Vec<(u16, i32)> = cells
        .iter()
        .enumerate()
        .filter(|(_, v)| **v != 0)
        .map(|(i, v)| (u16::try_from(i).unwrap_or(0), *v))
        .collect();
    let norm2 = cells
        .iter()
        .map(|(_, c)| i64::from(*c).saturating_mul(i64::from(*c)))
        .fold(0_i64, i64::saturating_add);
    Vector { cells, norm2 }
}

impl Vector {
    #[must_use]
    pub fn is_zero(&self) -> bool {
        self.norm2 == 0
    }

    #[must_use]
    pub fn cosine_permille(&self, other: &Self) -> u32 {
        if self.norm2 == 0 || other.norm2 == 0 {
            return 0;
        }
        let mut dot = 0_i64;
        let (mut i, mut j) = (0_usize, 0_usize);
        while let (Some((ia, va)), Some((ib, vb))) = (self.cells.get(i), other.cells.get(j)) {
            match ia.cmp(ib) {
                std::cmp::Ordering::Less => i = i.saturating_add(1),
                std::cmp::Ordering::Greater => j = j.saturating_add(1),
                std::cmp::Ordering::Equal => {
                    dot = dot.wrapping_add(i64::from(*va).wrapping_mul(i64::from(*vb)));
                    i = i.saturating_add(1);
                    j = j.saturating_add(1);
                }
            }
        }
        if dot <= 0 {
            return 0;
        }
        #[allow(clippy::cast_precision_loss)]
        let denom = (self.norm2 as f64).sqrt() * (other.norm2 as f64).sqrt();
        #[allow(clippy::cast_precision_loss)]
        let ratio = dot as f64 / denom;
        #[allow(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
        let value = (ratio * 1000.0 + 0.5).floor() as u32;
        value.min(1000)
    }
}
