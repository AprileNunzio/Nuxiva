pub const CHROMATIC_BINS: usize = 36;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum SemanticColor {
    AchromaticBlack,
    AchromaticGrey,
    AchromaticWhite,
    WarmRed,
    WarmOrange,
    WarmYellow,
    NatureGreen,
    CoolCyan,
    CoolBlue,
    RoyalPurple,
    VibrantMagenta,
}

impl SemanticColor {
    #[must_use]
    pub const fn key(self) -> &'static str {
        match self {
            Self::AchromaticBlack => "color.black",
            Self::AchromaticGrey => "color.grey",
            Self::AchromaticWhite => "color.white",
            Self::WarmRed => "color.red",
            Self::WarmOrange => "color.orange",
            Self::WarmYellow => "color.yellow",
            Self::NatureGreen => "color.green",
            Self::CoolCyan => "color.cyan",
            Self::CoolBlue => "color.blue",
            Self::RoyalPurple => "color.purple",
            Self::VibrantMagenta => "color.magenta",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct RgbSample {
    pub r: u8,
    pub g: u8,
    pub b: u8,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ColorPaletteProfile {
    pub dominant: SemanticColor,
    pub secondary: Option<SemanticColor>,
    pub luminance_bps: u16,
    pub saturation_bps: u16,
    pub histogram_bps: [u16; 11],
}

#[must_use]
pub fn classify_rgb_pixel(sample: RgbSample) -> (SemanticColor, u16, u16) {
    let r = u32::from(sample.r);
    let g = u32::from(sample.g);
    let b = u32::from(sample.b);
    let max_c = r.max(g).max(b);
    let min_c = r.min(g).min(b);
    let delta = max_c.saturating_sub(min_c);

    let lum_bps =
        u16::try_from(max_c.saturating_mul(10_000).checked_div(255).unwrap_or(0)).unwrap_or(10_000);
    let sat_bps = if max_c == 0 {
        0
    } else {
        u16::try_from(delta.saturating_mul(10_000).checked_div(max_c).unwrap_or(0))
            .unwrap_or(10_000)
    };

    if lum_bps < 1_800 {
        return (SemanticColor::AchromaticBlack, lum_bps, sat_bps);
    }
    if sat_bps < 1_600 {
        if lum_bps > 7_800 {
            return (SemanticColor::AchromaticWhite, lum_bps, sat_bps);
        }
        return (SemanticColor::AchromaticGrey, lum_bps, sat_bps);
    }

    let hue_deg: i32 = if delta == 0 {
        0
    } else if max_c == r {
        let num = i32::from(sample.g)
            .saturating_sub(i32::from(sample.b))
            .saturating_mul(60);
        num.checked_div(i32::try_from(delta).unwrap_or(1))
            .unwrap_or(0)
            .rem_euclid(360)
    } else if max_c == g {
        let num = i32::from(sample.b)
            .saturating_sub(i32::from(sample.r))
            .saturating_mul(60);
        num.checked_div(i32::try_from(delta).unwrap_or(1))
            .unwrap_or(0)
            .saturating_add(120)
            .rem_euclid(360)
    } else {
        let num = i32::from(sample.r)
            .saturating_sub(i32::from(sample.g))
            .saturating_mul(60);
        num.checked_div(i32::try_from(delta).unwrap_or(1))
            .unwrap_or(0)
            .saturating_add(240)
            .rem_euclid(360)
    };

    let color = match hue_deg {
        0..=18 | 345..=360 => SemanticColor::WarmRed,
        19..=45 => SemanticColor::WarmOrange,
        46..=72 => SemanticColor::WarmYellow,
        73..=165 => SemanticColor::NatureGreen,
        166..=200 => SemanticColor::CoolCyan,
        201..=255 => SemanticColor::CoolBlue,
        256..=295 => SemanticColor::RoyalPurple,
        _ => SemanticColor::VibrantMagenta,
    };

    (color, lum_bps, sat_bps)
}

#[must_use]
pub fn extract_color_palette(samples: &[RgbSample]) -> ColorPaletteProfile {
    let all_colors = [
        SemanticColor::AchromaticBlack,
        SemanticColor::AchromaticGrey,
        SemanticColor::AchromaticWhite,
        SemanticColor::WarmRed,
        SemanticColor::WarmOrange,
        SemanticColor::WarmYellow,
        SemanticColor::NatureGreen,
        SemanticColor::CoolCyan,
        SemanticColor::CoolBlue,
        SemanticColor::RoyalPurple,
        SemanticColor::VibrantMagenta,
    ];
    let mut counts = [0_u32; 11];
    let mut lum_sum: u64 = 0;
    let mut sat_sum: u64 = 0;

    if samples.is_empty() {
        return ColorPaletteProfile {
            dominant: SemanticColor::AchromaticGrey,
            secondary: None,
            luminance_bps: 5_000,
            saturation_bps: 0,
            histogram_bps: [0; 11],
        };
    }

    for s in samples {
        let (col, lum, sat) = classify_rgb_pixel(*s);
        lum_sum = lum_sum.saturating_add(u64::from(lum));
        sat_sum = sat_sum.saturating_add(u64::from(sat));
        if let Some(pos) = all_colors.iter().position(|c| *c == col)
            && let Some(slot) = counts.get_mut(pos)
        {
            *slot = slot.saturating_add(1);
        }
    }

    let total = u64::try_from(samples.len()).unwrap_or(1).max(1);
    let mut histogram_bps = [0_u16; 11];
    let mut ranked: Vec<(u32, SemanticColor)> = Vec::with_capacity(11);

    for (idx, col) in all_colors.iter().enumerate() {
        let c = counts.get(idx).copied().unwrap_or(0);
        let bps = u16::try_from(
            u64::from(c)
                .saturating_mul(10_000)
                .checked_div(total)
                .unwrap_or(0),
        )
        .unwrap_or(0);
        if let Some(h) = histogram_bps.get_mut(idx) {
            *h = bps;
        }
        ranked.push((c, *col));
    }

    ranked.sort_by_key(|a| std::cmp::Reverse(a.0));
    let dominant = ranked
        .first()
        .map_or(SemanticColor::AchromaticGrey, |(_, c)| *c);
    let secondary = ranked.get(1).filter(|(c, _)| *c > 0).map(|(_, col)| *col);

    ColorPaletteProfile {
        dominant,
        secondary,
        luminance_bps: u16::try_from(lum_sum.checked_div(total).unwrap_or(5_000)).unwrap_or(5_000),
        saturation_bps: u16::try_from(sat_sum.checked_div(total).unwrap_or(0)).unwrap_or(0),
        histogram_bps,
    }
}
