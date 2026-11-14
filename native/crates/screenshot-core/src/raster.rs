use std::io::Cursor;

use png::{BitDepth, ColorType, Compression, Decoder, Encoder, Transformations};

use crate::config::Mask;
use crate::error::{Error, Result};

pub const MAX_SIDE: u32 = 16_384;
pub const MAX_PIXELS: u64 = 120_000_000;
pub const MAX_PNG_BYTES: usize = 96 * 1024 * 1024;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Raster {
    pub width: u32,
    pub height: u32,
    pub rgb: Vec<u8>,
}

impl Raster {
    pub fn new(width: u32, height: u32, rgb: Vec<u8>) -> Result<Self> {
        if width == 0 || height == 0 || width > MAX_SIDE || height > MAX_SIDE {
            return Err(Error::Image("dimensions"));
        }
        let pixels = u64::from(width).saturating_mul(u64::from(height));
        if pixels > MAX_PIXELS || rgb.len() as u64 != pixels.saturating_mul(3) {
            return Err(Error::Image("buffer"));
        }
        Ok(Self { width, height, rgb })
    }

    pub fn decode(bytes: &[u8]) -> Result<Self> {
        if bytes.len() > MAX_PNG_BYTES {
            return Err(Error::Image("too_large"));
        }
        let mut decoder = Decoder::new(Cursor::new(bytes));
        decoder.set_transformations(Transformations::EXPAND | Transformations::STRIP_16);
        let mut reader = decoder.read_info().map_err(|_| Error::Image("decode"))?;
        let (width, height) = {
            let info = reader.info();
            (info.width, info.height)
        };
        if width == 0 || height == 0 || width > MAX_SIDE || height > MAX_SIDE {
            return Err(Error::Image("dimensions"));
        }
        if u64::from(width).saturating_mul(u64::from(height)) > MAX_PIXELS {
            return Err(Error::Image("dimensions"));
        }
        let mut buffer = vec![0; reader.output_buffer_size()];
        let frame = reader
            .next_frame(&mut buffer)
            .map_err(|_| Error::Image("decode"))?;
        let data = buffer
            .get(..frame.buffer_size())
            .ok_or(Error::Image("decode"))?;
        let rgb = match frame.color_type {
            ColorType::Rgb => data.to_vec(),
            ColorType::Rgba => data
                .chunks_exact(4)
                .flat_map(|p| p.iter().copied().take(3))
                .collect(),
            ColorType::Grayscale => data.iter().flat_map(|g| [*g, *g, *g]).collect(),
            ColorType::GrayscaleAlpha => data
                .chunks_exact(2)
                .flat_map(|p| {
                    let g = p.first().copied().unwrap_or(0);
                    [g, g, g]
                })
                .collect(),
            ColorType::Indexed => return Err(Error::Image("indexed")),
        };
        Self::new(width, height, rgb)
    }

    pub fn encode(&self) -> Result<Vec<u8>> {
        let mut out = Vec::new();
        {
            let mut encoder = Encoder::new(&mut out, self.width, self.height);
            encoder.set_color(ColorType::Rgb);
            encoder.set_depth(BitDepth::Eight);
            encoder.set_compression(Compression::Fast);
            let mut writer = encoder.write_header().map_err(|_| Error::Image("encode"))?;
            writer
                .write_image_data(&self.rgb)
                .map_err(|_| Error::Image("encode"))?;
        }
        if out.len() > MAX_PNG_BYTES {
            return Err(Error::Image("too_large"));
        }
        Ok(out)
    }

    pub fn apply_masks(&mut self, masks: &[Mask]) {
        let width = u64::from(self.width);
        let height = u64::from(self.height);
        for mask in masks {
            let x0 = width.saturating_mul(u64::from(mask.x)) / 1000;
            let y0 = height.saturating_mul(u64::from(mask.y)) / 1000;
            let x1 = (width.saturating_mul(u64::from(mask.x).saturating_add(u64::from(mask.w))))
                .div_ceil(1000)
                .min(width);
            let y1 = (height.saturating_mul(u64::from(mask.y).saturating_add(u64::from(mask.h))))
                .div_ceil(1000)
                .min(height);
            for y in y0..y1 {
                let start =
                    usize::try_from(y.saturating_mul(width).saturating_add(x0).saturating_mul(3));
                let end =
                    usize::try_from(y.saturating_mul(width).saturating_add(x1).saturating_mul(3));
                if let (Ok(start), Ok(end)) = (start, end) {
                    if let Some(row) = self.rgb.get_mut(start..end) {
                        row.fill(0);
                    }
                }
            }
        }
    }
}
