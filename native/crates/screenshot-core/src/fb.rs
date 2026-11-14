use std::fs;
use std::io::Read;
use std::path::Path;

use crate::error::{Error, Result};
use crate::raster::{MAX_PIXELS, MAX_SIDE, Raster};

const MAX_FB_BYTES: u64 = 256 * 1024 * 1024;

#[derive(Debug, Clone, Copy)]
pub struct Geometry {
    pub width: u32,
    pub height: u32,
    pub bpp: u32,
    pub stride: usize,
}

fn read_trim(path: &Path) -> Option<String> {
    fs::read_to_string(path).ok().map(|s| s.trim().to_owned())
}

pub fn geometry(sys: &Path, index: u32) -> Result<Geometry> {
    let base = sys.join(format!("fb{index}"));
    let size = read_trim(&base.join("virtual_size")).ok_or(Error::Capture("fb_geometry"))?;
    let (w, h) = size.split_once(',').ok_or(Error::Capture("fb_geometry"))?;
    let width: u32 = w.parse().map_err(|_| Error::Capture("fb_geometry"))?;
    let height: u32 = h.parse().map_err(|_| Error::Capture("fb_geometry"))?;
    let bpp: u32 = read_trim(&base.join("bits_per_pixel"))
        .and_then(|v| v.parse().ok())
        .ok_or(Error::Capture("fb_geometry"))?;
    let bytes_per = usize::try_from(bpp / 8).map_err(|_| Error::Capture("fb_geometry"))?;
    let default_stride = usize::try_from(width)
        .map_err(|_| Error::Capture("fb_geometry"))?
        .saturating_mul(bytes_per);
    let stride = read_trim(&base.join("stride"))
        .and_then(|v| v.parse().ok())
        .unwrap_or(default_stride);
    if width == 0
        || height == 0
        || width > MAX_SIDE
        || height > MAX_SIDE
        || !matches!(bpp, 16 | 24 | 32)
        || stride < default_stride
    {
        return Err(Error::Capture("fb_geometry"));
    }
    Ok(Geometry {
        width,
        height,
        bpp,
        stride,
    })
}

pub fn convert(raw: &[u8], geo: &Geometry) -> Result<Raster> {
    let pixels = u64::from(geo.width).saturating_mul(u64::from(geo.height));
    if pixels > MAX_PIXELS {
        return Err(Error::Capture("fb_geometry"));
    }
    let width = usize::try_from(geo.width).map_err(|_| Error::Capture("fb_geometry"))?;
    let mut rgb = Vec::with_capacity(usize::try_from(pixels.saturating_mul(3)).unwrap_or(0));
    for row in raw.chunks(geo.stride).take(geo.height as usize) {
        match geo.bpp {
            32 => {
                for px in row.chunks_exact(4).take(width) {
                    let [b, g, r, _] = [px.first(), px.get(1), px.get(2), px.get(3)]
                        .map(|v| v.copied().unwrap_or(0));
                    rgb.extend_from_slice(&[r, g, b]);
                }
            }
            24 => {
                for px in row.chunks_exact(3).take(width) {
                    let [b, g, r] =
                        [px.first(), px.get(1), px.get(2)].map(|v| v.copied().unwrap_or(0));
                    rgb.extend_from_slice(&[r, g, b]);
                }
            }
            _ => {
                for px in row.chunks_exact(2).take(width) {
                    let lo = u16::from(px.first().copied().unwrap_or(0));
                    let hi = u16::from(px.get(1).copied().unwrap_or(0));
                    let v = (hi << 8) | lo;
                    let r = ((v >> 11) & 0x1f) as u8;
                    let g = ((v >> 5) & 0x3f) as u8;
                    let b = (v & 0x1f) as u8;
                    rgb.extend_from_slice(&[
                        (r << 3) | (r >> 2),
                        (g << 2) | (g >> 4),
                        (b << 3) | (b >> 2),
                    ]);
                }
            }
        }
    }
    Raster::new(geo.width, geo.height, rgb)
}

pub fn capture(sys: &Path, dev: &Path, index: u32) -> Result<Raster> {
    let geo = geometry(sys, index)?;
    let expected = u64::try_from(geo.stride)
        .unwrap_or(u64::MAX)
        .saturating_mul(u64::from(geo.height));
    if expected > MAX_FB_BYTES {
        return Err(Error::Capture("fb_too_large"));
    }
    let mut file =
        fs::File::open(dev.join(format!("fb{index}"))).map_err(|_| Error::Capture("fb_open"))?;
    let mut raw = Vec::new();
    file.by_ref()
        .take(expected)
        .read_to_end(&mut raw)
        .map_err(|_| Error::Capture("fb_read"))?;
    if (raw.len() as u64) < expected {
        return Err(Error::Capture("fb_short"));
    }
    convert(&raw, &geo)
}
