use sha2::{Digest, Sha256};

use crate::dtw;
use crate::error::{WakeError, WakeResult};
use crate::mel::{self, Ceps, DIM, Feat, RATE};
use crate::vad;

pub const MIN_RECORDINGS: usize = 3;
pub const MAX_RECORDINGS: usize = 10;
pub const MIN_FRAMES: usize = 35;
pub const MAX_FRAMES: usize = 200;
const MIN_SAMPLES: usize = RATE / 2;
const MAX_SAMPLES: usize = RATE * 4;
const THRESHOLD_SLACK: f32 = 1.45;
const MIN_THRESHOLD: f32 = 0.25;
const MAX_THRESHOLD: f32 = 1.1;
const OUTLIER_RATIO: f32 = 2.5;
const MAGIC: &[u8; 4] = b"NXWK";
const VERSION: u8 = 1;
const MAX_TEMPLATES: usize = MAX_RECORDINGS;
const HEADER: usize = 4 + 1 + 1 + 2 + 4 + 2;

#[derive(Debug, Clone, PartialEq)]
pub struct Model {
    templates: Vec<Vec<Feat>>,
    threshold: f32,
    reference: usize,
}

fn recording_features(pcm: &[i16], index: usize) -> WakeResult<Vec<Feat>> {
    if pcm.len() < MIN_SAMPLES || pcm.len() > MAX_SAMPLES {
        return Err(WakeError::RecordingLength(index));
    }
    let frames = mel::frames_of(&mel::to_float(pcm));
    let (start, end) = vad::trim(&frames).ok_or(WakeError::NoSpeech(index))?;
    let span = end.saturating_sub(start);
    if !(MIN_FRAMES..=MAX_FRAMES).contains(&span) {
        return Err(WakeError::NoSpeech(index));
    }
    let ceps: Vec<Ceps> = frames
        .get(start..end)
        .ok_or(WakeError::NoSpeech(index))?
        .iter()
        .map(|f| f.ceps)
        .collect();
    Ok(mel::features(&ceps))
}

fn pairwise(items: &[Vec<Feat>]) -> WakeResult<Vec<Vec<f32>>> {
    let n = items.len();
    let mut grid = vec![vec![0.0f32; n]; n];
    for i in 0..n {
        for j in (i.saturating_add(1))..n {
            let a = items.get(i).ok_or(WakeError::Model)?;
            let b = items.get(j).ok_or(WakeError::Model)?;
            let d = dtw::distance(a, b, f32::INFINITY).ok_or(WakeError::Inconsistent(j))?;
            if let Some(cell) = grid.get_mut(i).and_then(|r| r.get_mut(j)) {
                *cell = d;
            }
            if let Some(cell) = grid.get_mut(j).and_then(|r| r.get_mut(i)) {
                *cell = d;
            }
        }
    }
    Ok(grid)
}

fn nearest(row: &[f32], skip: usize) -> f32 {
    row.iter()
        .enumerate()
        .filter(|(k, _)| *k != skip)
        .map(|(_, v)| *v)
        .fold(f32::INFINITY, f32::min)
}

impl Model {
    pub fn enroll(recordings: &[Vec<i16>]) -> WakeResult<Self> {
        if recordings.len() < MIN_RECORDINGS {
            return Err(WakeError::TooFewRecordings);
        }
        if recordings.len() > MAX_RECORDINGS {
            return Err(WakeError::TooManyRecordings);
        }
        let items = recordings
            .iter()
            .enumerate()
            .map(|(i, pcm)| recording_features(pcm, i))
            .collect::<WakeResult<Vec<_>>>()?;
        let grid = pairwise(&items)?;
        let nns: Vec<f32> = grid
            .iter()
            .enumerate()
            .map(|(i, r)| nearest(r, i))
            .collect();
        let mut sorted = nns.clone();
        sorted.sort_by(f32::total_cmp);
        let median = sorted
            .get(sorted.len() / 2)
            .copied()
            .ok_or(WakeError::Model)?;
        if let Some(bad) = nns
            .iter()
            .position(|d| *d > median * OUTLIER_RATIO && *d > MIN_THRESHOLD)
        {
            return Err(WakeError::Inconsistent(bad));
        }
        let worst_nn = nns.iter().copied().fold(0.0f32, f32::max);
        let threshold = (worst_nn * THRESHOLD_SLACK).clamp(MIN_THRESHOLD, MAX_THRESHOLD);
        let reference = {
            let mut lens: Vec<usize> = items.iter().map(Vec::len).collect();
            lens.sort_unstable();
            lens.get(lens.len() / 2).copied().ok_or(WakeError::Model)?
        };
        Ok(Self {
            templates: items,
            threshold,
            reference,
        })
    }

    #[must_use]
    pub fn threshold(&self) -> f32 {
        self.threshold
    }

    #[must_use]
    pub fn reference_frames(&self) -> usize {
        self.reference
    }

    #[must_use]
    pub fn templates(&self) -> &[Vec<Feat>] {
        &self.templates
    }

    #[must_use]
    pub fn to_bytes(&self) -> Vec<u8> {
        let mut out = Vec::with_capacity(HEADER);
        out.extend_from_slice(MAGIC);
        out.push(VERSION);
        out.push(u8::try_from(DIM).unwrap_or(0));
        out.extend_from_slice(
            &u16::try_from(self.templates.len())
                .unwrap_or(0)
                .to_le_bytes(),
        );
        out.extend_from_slice(&self.threshold.to_le_bytes());
        out.extend_from_slice(&u16::try_from(self.reference).unwrap_or(0).to_le_bytes());
        for t in &self.templates {
            out.extend_from_slice(&u16::try_from(t.len()).unwrap_or(0).to_le_bytes());
            for frame in t {
                for v in frame {
                    out.extend_from_slice(&v.to_le_bytes());
                }
            }
        }
        let digest = Sha256::digest(&out);
        out.extend_from_slice(&digest);
        out
    }

    pub fn from_bytes(raw: &[u8]) -> WakeResult<Self> {
        let split = raw.len().checked_sub(32).ok_or(WakeError::Model)?;
        let (body, tail) = raw.split_at(split);
        if Sha256::digest(body).as_slice() != tail {
            return Err(WakeError::Checksum);
        }
        let mut cur = Cursor { data: body, at: 0 };
        if cur.take(4)? != MAGIC || cur.byte()? != VERSION || usize::from(cur.byte()?) != DIM {
            return Err(WakeError::Model);
        }
        let count = usize::from(cur.u16()?);
        let threshold = cur.f32()?;
        let reference = usize::from(cur.u16()?);
        if count == 0
            || count > MAX_TEMPLATES
            || !(MIN_THRESHOLD..=MAX_THRESHOLD).contains(&threshold)
            || !(MIN_FRAMES..=MAX_FRAMES).contains(&reference)
        {
            return Err(WakeError::Model);
        }
        let mut templates = Vec::with_capacity(count);
        for _ in 0..count {
            let frames = usize::from(cur.u16()?);
            if !(MIN_FRAMES..=MAX_FRAMES).contains(&frames) {
                return Err(WakeError::Model);
            }
            let mut template = Vec::with_capacity(frames);
            for _ in 0..frames {
                let mut feat = [0.0f32; DIM];
                for cell in &mut feat {
                    *cell = cur.f32()?;
                }
                template.push(feat);
            }
            templates.push(template);
        }
        if cur.at != body.len() {
            return Err(WakeError::Model);
        }
        Ok(Self {
            templates,
            threshold,
            reference,
        })
    }
}

struct Cursor<'a> {
    data: &'a [u8],
    at: usize,
}

impl Cursor<'_> {
    fn take(&mut self, n: usize) -> WakeResult<&[u8]> {
        let end = self.at.checked_add(n).ok_or(WakeError::Model)?;
        let slice = self.data.get(self.at..end).ok_or(WakeError::Model)?;
        self.at = end;
        Ok(slice)
    }

    fn byte(&mut self) -> WakeResult<u8> {
        self.take(1)?.first().copied().ok_or(WakeError::Model)
    }

    fn u16(&mut self) -> WakeResult<u16> {
        let b: [u8; 2] = self.take(2)?.try_into().map_err(|_| WakeError::Model)?;
        Ok(u16::from_le_bytes(b))
    }

    fn f32(&mut self) -> WakeResult<f32> {
        let b: [u8; 4] = self.take(4)?.try_into().map_err(|_| WakeError::Model)?;
        let v = f32::from_le_bytes(b);
        if v.is_finite() {
            Ok(v)
        } else {
            Err(WakeError::Model)
        }
    }
}
