use crate::net::{Addr, ip};

pub const MAX_ROWS: usize = 4_000_000;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GeoError {
    Empty,
    TooLarge,
    Corrupt,
}

impl GeoError {
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::Empty => "geo.empty",
            Self::TooLarge => "geo.too_large",
            Self::Corrupt => "geo.corrupt",
        }
    }
}

#[derive(Debug, Default, Clone)]
pub struct GeoTable {
    v4: Vec<(u32, u32, [u8; 2])>,
    v6: Vec<(u128, u128, [u8; 2])>,
}

fn country(raw: &str) -> Option<[u8; 2]> {
    let bytes = raw.trim().trim_matches('"').as_bytes();
    match bytes {
        [a, b] if a.is_ascii_uppercase() && b.is_ascii_uppercase() && bytes != b"ZZ" => {
            Some([*a, *b])
        }
        _ => None,
    }
}

fn find<T: Ord + Copy>(rows: &[(T, T, [u8; 2])], key: T) -> Option<[u8; 2]> {
    let index = rows.partition_point(|row| row.0 <= key).checked_sub(1)?;
    let row = rows.get(index)?;
    (key <= row.1).then_some(row.2)
}

fn ordered<T: Ord + Copy>(rows: &mut [(T, T, [u8; 2])]) -> bool {
    rows.sort_unstable_by_key(|row| row.0);
    rows.windows(2).all(|pair| match pair {
        [a, b] => a.1 < b.0,
        _ => true,
    })
}

impl GeoTable {
    pub fn parse(text: &str) -> Result<Self, GeoError> {
        let mut table = Self::default();
        let mut bad = 0_usize;
        let mut rows = 0_usize;
        for line in text.lines() {
            let line = line.trim();
            if line.is_empty() || line.starts_with('#') {
                continue;
            }
            rows = rows.saturating_add(1);
            if rows > MAX_ROWS {
                return Err(GeoError::TooLarge);
            }
            let mut parts = line.split(',');
            let (Some(first), Some(last), Some(label)) = (parts.next(), parts.next(), parts.next())
            else {
                bad = bad.saturating_add(1);
                continue;
            };
            let code = country(label);
            match (
                ip(first.trim_matches('"')),
                ip(last.trim_matches('"')),
                code,
            ) {
                (Some(Addr::V4(start)), Some(Addr::V4(end)), Some(code)) if start <= end => {
                    table.v4.push((start, end, code));
                }
                (Some(Addr::V6(start)), Some(Addr::V6(end)), Some(code)) if start <= end => {
                    table.v6.push((start, end, code));
                }
                (_, _, None)
                    if label.trim().trim_matches('"') == "ZZ" || label.trim().is_empty() => {}
                _ => bad = bad.saturating_add(1),
            }
        }
        let size = table.len();
        if size == 0 {
            return Err(GeoError::Empty);
        }
        if bad.saturating_mul(100) > size {
            return Err(GeoError::Corrupt);
        }
        if !ordered(&mut table.v4) || !ordered(&mut table.v6) {
            return Err(GeoError::Corrupt);
        }
        Ok(table)
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.v4.len().saturating_add(self.v6.len())
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }

    #[must_use]
    pub fn lookup(&self, raw: &str) -> Option<String> {
        let code = match ip(raw)? {
            Addr::V4(v) => find(&self.v4, v)?,
            Addr::V6(v) => find(&self.v6, v)?,
            Addr::Mac(_) => return None,
        };
        Some(String::from_utf8_lossy(&code).into_owned())
    }
}
