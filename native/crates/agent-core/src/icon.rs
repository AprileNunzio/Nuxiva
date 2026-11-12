const SIZE: u32 = 64;

const PALETTE: &[(&str, [u8; 3])] = &[
    ("creativita", [168, 123, 255]),
    ("percezione", [76, 230, 255]),
    ("cognizione", [255, 209, 102]),
    ("sicurezza", [255, 99, 99]),
    ("domotica", [112, 224, 0]),
    ("infrastruttura", [100, 160, 255]),
    ("multimedia", [255, 107, 229]),
    ("comunicazione", [94, 242, 255]),
    ("conoscenza", [255, 159, 28]),
    ("salute", [46, 196, 182]),
    ("sport", [56, 176, 0]),
    ("scienza", [131, 56, 236]),
    ("informatica", [72, 191, 227]),
];

fn crc32(bytes: &[u8]) -> u32 {
    let mut crc: u32 = 0xffff_ffff;
    for &b in bytes {
        crc ^= u32::from(b);
        for _ in 0..8 {
            let mask = (crc & 1).wrapping_neg();
            crc = (crc >> 1) ^ (0xedb8_8320 & mask);
        }
    }
    !crc
}

fn adler32(bytes: &[u8]) -> u32 {
    let (mut a, mut b) = (1u32, 0u32);
    for &x in bytes {
        a = a.wrapping_add(u32::from(x)) % 65_521;
        b = b.wrapping_add(a) % 65_521;
    }
    (b << 16) | a
}

fn chunk(out: &mut Vec<u8>, kind: [u8; 4], data: &[u8]) {
    out.extend_from_slice(&u32::try_from(data.len()).unwrap_or(0).to_be_bytes());
    let mut body = Vec::with_capacity(data.len().saturating_add(4));
    body.extend_from_slice(&kind);
    body.extend_from_slice(data);
    out.extend_from_slice(&body);
    out.extend_from_slice(&crc32(&body).to_be_bytes());
}

fn zlib_stored(raw: &[u8]) -> Vec<u8> {
    let mut out = vec![0x78, 0x01];
    let blocks: Vec<&[u8]> = raw.chunks(65_535).collect();
    let last = blocks.len().saturating_sub(1);
    for (i, block) in blocks.iter().enumerate() {
        out.push(u8::from(i == last));
        let len = u16::try_from(block.len()).unwrap_or(u16::MAX);
        out.extend_from_slice(&len.to_le_bytes());
        out.extend_from_slice(&(!len).to_le_bytes());
        out.extend_from_slice(block);
    }
    out.extend_from_slice(&adler32(raw).to_be_bytes());
    out
}

fn color(category: &str) -> [u8; 3] {
    PALETTE
        .iter()
        .find(|(name, _)| *name == category)
        .map_or([155, 231, 255], |(_, c)| *c)
}

fn seed(id: &str) -> u32 {
    id.bytes().fold(0x811c_9dc5u32, |h, b| {
        (h ^ u32::from(b)).wrapping_mul(0x0100_0193)
    })
}

fn mix(base: u8, toward: u8, weight: u32) -> u8 {
    let w = weight.min(255);
    let value = u32::from(base)
        .wrapping_mul(255u32.wrapping_sub(w))
        .wrapping_add(u32::from(toward).wrapping_mul(w))
        / 255;
    u8::try_from(value).unwrap_or(u8::MAX)
}

fn pixel(px: u32, py: u32, rgb: [u8; 3], spot: (i64, i64)) -> [u8; 4] {
    let center = i64::from(SIZE / 2);
    let (dx, dy) = (
        i64::from(px).saturating_sub(center),
        i64::from(py).saturating_sub(center),
    );
    let d2 = dx.saturating_mul(dx).saturating_add(dy.saturating_mul(dy));
    let outer = 28i64.saturating_mul(28);
    let edge = 26i64.saturating_mul(26);
    if d2 > outer {
        return [0, 0, 0, 0];
    }
    let alpha = if d2 > edge {
        let span = outer.saturating_sub(edge).max(1);
        u8::try_from(
            outer
                .saturating_sub(d2)
                .saturating_mul(255)
                .checked_div(span)
                .unwrap_or(255),
        )
        .unwrap_or(255)
    } else {
        255
    };
    let (sx, sy) = (
        i64::from(px).saturating_sub(spot.0),
        i64::from(py).saturating_sub(spot.1),
    );
    let s2 = sx.saturating_mul(sx).saturating_add(sy.saturating_mul(sy));
    let glow = u32::try_from(200i64.saturating_sub(s2 / 3).max(0)).unwrap_or(0);
    let shade = u32::try_from((d2 / 8).min(120)).unwrap_or(0);
    let [red, green, blue] = rgb.map(|v| mix(mix(v, 255, glow), 0, shade));
    [red, green, blue, alpha]
}

#[must_use]
pub fn render(category: &str, id: &str) -> Vec<u8> {
    let rgb = color(category);
    let h = seed(id);
    let spot = (
        i64::from((h % 12).wrapping_add(20)),
        i64::from(((h >> 8) % 10).wrapping_add(18)),
    );
    let row = usize::try_from(SIZE.saturating_mul(4).saturating_add(1)).unwrap_or(0);
    let mut raw = Vec::with_capacity(row.saturating_mul(usize::try_from(SIZE).unwrap_or(0)));
    for y in 0..SIZE {
        raw.push(0);
        for x in 0..SIZE {
            raw.extend_from_slice(&pixel(x, y, rgb, spot));
        }
    }
    let mut png = vec![0x89, b'P', b'N', b'G', 0x0d, 0x0a, 0x1a, 0x0a];
    let mut ihdr = Vec::with_capacity(13);
    ihdr.extend_from_slice(&SIZE.to_be_bytes());
    ihdr.extend_from_slice(&SIZE.to_be_bytes());
    ihdr.extend_from_slice(&[8, 6, 0, 0, 0]);
    chunk(&mut png, *b"IHDR", &ihdr);
    chunk(&mut png, *b"IDAT", &zlib_stored(&raw));
    chunk(&mut png, *b"IEND", &[]);
    png
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn crc_matches_reference() {
        assert_eq!(crc32(b"IEND"), 0xae42_6082);
        assert_eq!(adler32(b"Wikipedia"), 0x11e6_0398);
    }

    #[test]
    fn renders_a_valid_png_header_and_size() {
        let png = render("salute", "medico");
        assert_eq!(
            png.get(..8),
            Some(&[0x89, b'P', b'N', b'G', 0x0d, 0x0a, 0x1a, 0x0a][..])
        );
        assert!(png.len() > 16_000);
        assert_eq!(
            png.get(png.len().saturating_sub(8)..),
            Some(&[b'I', b'E', b'N', b'D', 0xae, 0x42, 0x60, 0x82][..])
        );
    }
}
