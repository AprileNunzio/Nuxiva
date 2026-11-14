use crate::{Audio, Control, DuplexError, Pacer, PacerSettings, Pcm, Settings, parse_wav};

fn wav(rate: u32, channels: u16, samples: &[i16]) -> Vec<u8> {
    let data: Vec<u8> = samples.iter().flat_map(|s| s.to_le_bytes()).collect();
    let mut out = Vec::new();
    out.extend_from_slice(b"RIFF");
    out.extend_from_slice(&(36 + data.len() as u32).to_le_bytes());
    out.extend_from_slice(b"WAVEfmt ");
    out.extend_from_slice(&16u32.to_le_bytes());
    out.extend_from_slice(&1u16.to_le_bytes());
    out.extend_from_slice(&channels.to_le_bytes());
    out.extend_from_slice(&rate.to_le_bytes());
    out.extend_from_slice(&(rate * u32::from(channels) * 2).to_le_bytes());
    out.extend_from_slice(&(channels * 2).to_le_bytes());
    out.extend_from_slice(&16u16.to_le_bytes());
    out.extend_from_slice(b"data");
    out.extend_from_slice(&(data.len() as u32).to_le_bytes());
    out.extend_from_slice(&data);
    out
}

fn tone(rate: u32, ms: u32) -> Pcm {
    Pcm {
        rate_hz: rate,
        samples: (0..rate * ms / 1000).map(|i| (i % 200) as i16).collect(),
    }
}

#[test]
fn a_mono_wav_round_trips() {
    let pcm = parse_wav(&wav(24_000, 1, &[1, -2, 3, -4])).expect("wav");
    assert_eq!(pcm.rate_hz, 24_000);
    assert_eq!(pcm.samples, vec![1, -2, 3, -4]);
    assert_eq!(pcm.to_bytes().len(), 8);
}

#[test]
fn stereo_is_averaged_to_mono() {
    let pcm = parse_wav(&wav(16_000, 2, &[10, 30, -10, -30])).expect("wav");
    assert_eq!(pcm.samples, vec![20, -20]);
}

#[test]
fn malformed_wavs_are_rejected() {
    let good = wav(24_000, 1, &[1, 2, 3, 4]);
    assert!(parse_wav(&[]).is_err());
    assert!(parse_wav(b"RIFF....WAVE").is_err());
    assert!(parse_wav(&good[..30]).is_err());
    let mut bad = good.clone();
    bad[20] = 3;
    assert_eq!(parse_wav(&bad), Err(DuplexError::Invalid));
    let mut rate = good.clone();
    rate[24..28].copy_from_slice(&1_000u32.to_le_bytes());
    assert_eq!(parse_wav(&rate), Err(DuplexError::Invalid));
    let mut bits = good.clone();
    bits[34] = 8;
    assert_eq!(parse_wav(&bits), Err(DuplexError::Invalid));
    let mut huge = good.clone();
    huge[16..20].copy_from_slice(&u32::MAX.to_le_bytes());
    assert_eq!(parse_wav(&huge), Err(DuplexError::Parse));
    assert_eq!(
        parse_wav(&vec![0; 17 * 1024 * 1024]),
        Err(DuplexError::TooLarge)
    );
    assert_eq!(parse_wav(&wav(24_000, 1, &[])), Err(DuplexError::Invalid));
}

#[test]
fn a_streaming_header_with_unknown_length_is_clamped_to_the_payload() {
    let mut w = wav(24_000, 1, &[5, 6, 7]);
    let at = w.len() - 6 - 4;
    w[at..at + 4].copy_from_slice(&u32::MAX.to_le_bytes());
    assert_eq!(parse_wav(&w).expect("wav").samples, vec![5, 6, 7]);
}

#[test]
fn odd_sized_chunks_before_data_are_skipped() {
    let mut w = wav(24_000, 1, &[9, 9]);
    let extra = [b'L', b'I', b'S', b'T', 3, 0, 0, 0, 1, 2, 3, 0];
    w.splice(36..36, extra);
    assert_eq!(parse_wav(&w).expect("wav").samples, vec![9, 9]);
}

#[test]
fn frames_have_fixed_duration_and_decode_back() {
    let mut pacer = Pacer::new(PacerSettings::default()).expect("pacer");
    let info = pacer.push(1, 7, &tone(24_000, 400)).expect("push");
    assert_eq!(info.frames, 10);
    assert_eq!(info.duration_ms, 400);
    let frames = pacer.poll(0, 1);
    assert!(!frames.is_empty());
    let first = &frames[0];
    assert_eq!(first.pcm.len(), 24_000 * 40 / 1000 * 2);
    let decoded = Audio::decode(&first.encode(), &Settings::default()).expect("decode");
    assert_eq!((decoded.epoch, decoded.seq), (1, 7));
}

#[test]
fn the_lead_limits_how_much_audio_is_in_flight() {
    let mut pacer = Pacer::new(PacerSettings::default()).expect("pacer");
    pacer.push(1, 1, &tone(24_000, 2_000)).expect("push");
    let burst = pacer.poll(0, 1);
    assert!(burst.len() >= 6 && burst.len() <= 7);
    assert!(pacer.in_flight_ms(0) <= 280);
    assert!(pacer.poll(0, 1).is_empty());
    assert_eq!(pacer.poll(80, 1).len(), 2);
    let mut sent = burst.len() + 2;
    let mut now = 80;
    while pacer.queued_frames() > 0 {
        now += 10;
        sent += pacer.poll(now, 1).len();
    }
    assert_eq!(sent, 50);
    assert!(now <= 2_000);
}

#[test]
fn cancel_drops_everything_queued_at_once() {
    let mut pacer = Pacer::new(PacerSettings::default()).expect("pacer");
    pacer.push(1, 1, &tone(24_000, 2_000)).expect("push");
    let sent = pacer.poll(0, 1).len();
    let dropped = pacer.cancel();
    assert_eq!(dropped.frames as usize, 50 - sent);
    assert_eq!(pacer.queued_frames(), 0);
    assert!(pacer.poll(10_000, 1).is_empty());
    assert_eq!(pacer.in_flight_ms(0), 0);
}

#[test]
fn stale_epochs_are_discarded_on_poll() {
    let mut pacer = Pacer::new(PacerSettings::default()).expect("pacer");
    pacer.push(1, 1, &tone(24_000, 200)).expect("push");
    pacer.push(2, 1, &tone(24_000, 80)).expect("push");
    let out = pacer.poll(0, 2);
    assert!(out.iter().all(|a| a.epoch == 2));
    assert_eq!(out.len(), 2);
}

#[test]
fn an_underrun_rebases_the_clock() {
    let mut pacer = Pacer::new(PacerSettings::default()).expect("pacer");
    pacer.push(1, 1, &tone(24_000, 80)).expect("push");
    assert_eq!(pacer.poll(0, 1).len(), 2);
    pacer.push(1, 2, &tone(24_000, 80)).expect("push");
    assert_eq!(pacer.poll(5_000, 1).len(), 2);
    assert!(pacer.in_flight_ms(5_000) <= 80);
}

#[test]
fn high_rates_still_fit_the_frame_limit() {
    let mut pacer = Pacer::new(PacerSettings {
        frame_ms: 100,
        lead_ms: 300,
    })
    .expect("pacer");
    pacer.push(1, 1, &tone(48_000, 500)).expect("push");
    for a in pacer.poll(0, 1) {
        assert!(a.pcm.len() <= 4_096);
        assert!(Audio::decode(&a.encode(), &Settings::default()).is_ok());
    }
}

#[test]
fn the_queue_is_bounded() {
    let mut pacer = Pacer::new(PacerSettings::default()).expect("pacer");
    let big = tone(24_000, 60_000);
    let mut refused = false;
    for _ in 0..4 {
        refused |= pacer.push(1, 1, &big) == Err(DuplexError::Capacity);
    }
    assert!(refused);
    assert!(pacer.queued_frames() <= 4_096);
}

#[test]
fn settings_are_validated() {
    for bad in [
        PacerSettings {
            frame_ms: 5,
            lead_ms: 240,
        },
        PacerSettings {
            frame_ms: 200,
            lead_ms: 240,
        },
        PacerSettings {
            frame_ms: 40,
            lead_ms: 20,
        },
        PacerSettings {
            frame_ms: 40,
            lead_ms: 5_000,
        },
    ] {
        assert!(Pacer::new(bad).is_err());
    }
}

#[test]
fn the_chunk_control_frame_round_trips_and_rejects_extra_fields() {
    let settings = Settings::default();
    let frame = Control::Chunk {
        epoch: 3,
        seq: 2,
        rate_hz: 24_000,
        frames: 12,
    };
    let text = frame.encode().expect("encode");
    assert!(text.contains("\"gen\":3"));
    assert_eq!(Control::parse(&text, &settings).expect("parse"), frame);
    let extra = text.replace('}', ",\"x\":1}");
    assert!(Control::parse(&extra, &settings).is_err());
}
