use model_fit::Quant;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum Precision {
    F16,
    Q8,
    Q6,
    Q5,
    Q4,
    Q3,
    Q2,
    Q1,
}

impl Precision {
    #[must_use]
    pub const fn to_fit(self) -> Option<Quant> {
        match self {
            Self::F16 => Some(Quant::F16),
            Self::Q8 => Some(Quant::Q8),
            Self::Q6 => Some(Quant::Q6),
            Self::Q5 => Some(Quant::Q5),
            Self::Q4 => Some(Quant::Q4),
            Self::Q3 => Some(Quant::Q3),
            Self::Q2 => Some(Quant::Q2),
            Self::Q1 => None,
        }
    }

    #[must_use]
    pub const fn agentic_ok(self) -> bool {
        !matches!(self, Self::Q1)
    }
}

fn token(raw: &str) -> Option<Precision> {
    let upper = raw.to_ascii_uppercase();
    let core = upper.strip_prefix("UD-").unwrap_or(&upper);
    if matches!(core, "BF16" | "F16" | "FP16") {
        return Some(Precision::F16);
    }
    if matches!(core, "MXFP4" | "NVFP4") {
        return Some(Precision::Q4);
    }
    let digits = core
        .strip_prefix("IQ")
        .or_else(|| core.strip_prefix("TQ"))
        .or_else(|| core.strip_prefix('Q'))?;
    let mut parts = digits.splitn(2, '_');
    let bits = parts.next()?;
    let rest = parts.next().unwrap_or_default();
    let tail_ok = rest.split('_').all(|p| {
        matches!(
            p,
            "" | "0" | "1" | "K" | "S" | "M" | "L" | "XL" | "XS" | "XXS" | "NL"
        )
    });
    if !tail_ok {
        return None;
    }
    match bits {
        "8" => Some(Precision::Q8),
        "6" => Some(Precision::Q6),
        "5" => Some(Precision::Q5),
        "4" => Some(Precision::Q4),
        "3" => Some(Precision::Q3),
        "2" => Some(Precision::Q2),
        "1" => Some(Precision::Q1),
        _ => None,
    }
}

#[must_use]
pub fn parse_precision(name: &str) -> Option<Precision> {
    if name.len() > 256 {
        return None;
    }
    let stem = name
        .trim()
        .trim_end_matches(".gguf")
        .trim_end_matches(".GGUF");
    let last = stem.rsplit(['/', ':']).next().unwrap_or(stem);
    if let Some(found) = token(last) {
        return Some(found);
    }
    let pieces: Vec<&str> = last.split(['-', '.']).collect();
    pieces
        .windows(2)
        .rev()
        .find_map(|pair| match pair {
            [first, second] if first.eq_ignore_ascii_case("UD") => token(second),
            _ => None,
        })
        .or_else(|| pieces.iter().rev().find_map(|p| token(p)))
}
