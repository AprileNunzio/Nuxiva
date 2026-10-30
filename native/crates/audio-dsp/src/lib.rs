#![forbid(unsafe_code)]

pub mod cleaner;
pub mod device_router;
pub mod enhancer;
pub mod filter;
pub mod media_awareness;
pub mod parallel_runtime;
pub mod pcm;
pub mod vad;
pub mod voice_biomarkers;

pub use cleaner::{AudioCleaner, CleanedFrame};
pub use device_router::{
    AudioDevice, DeviceSelectionMode, FailoverDeviceRouter, MultiMicTriage, SatelliteAudioReport,
};
pub use enhancer::{AcousticFeatures, EnhancedSignal, SignalEnhancer};
pub use filter::BandpassFilter300_3400;
pub use media_awareness::{AcousticEchoSuppressor, MediaPlaybackState, MediaStreamType};
pub use parallel_runtime::{ConcurrentAudioPipeline, PipelineTask, PipelineTaskStatus};
pub use pcm::{MAX_FRAME_BYTES, PcmError};
pub use vad::{SpectralEntropyVad, VadDecision, VadResult};
pub use voice_biomarkers::{VoiceBiomarkerAnalyzer, VoiceBiomarkers};

#[cfg(test)]
mod tests {
    use super::*;

    fn generate_sine_wave(
        freq_hz: f32,
        sample_rate: f32,
        num_samples: usize,
        amplitude: f32,
    ) -> Vec<i16> {
        let mut buffer = Vec::with_capacity(num_samples);
        for i in 0..num_samples {
            #[allow(clippy::cast_precision_loss)]
            let t = (i as f32) / sample_rate;
            let val = (2.0 * std::f32::consts::PI * freq_hz * t).sin() * amplitude;
            #[allow(clippy::cast_possible_truncation)]
            buffer.push(val.clamp(-32_768.0, 32_767.0) as i16);
        }
        buffer
    }

    #[test]
    fn test_bandpass_filter_attenuates_low_rumble() {
        let mut filter = BandpassFilter300_3400::new();
        let rumble_50hz = generate_sine_wave(50.0, 16_000.0, 320, 10_000.0);
        let mut out = Vec::new();
        filter.process_buffer(&rumble_50hz, &mut out);

        let in_rms = SpectralEntropyVad::compute_rms(&rumble_50hz);
        let out_rms = SpectralEntropyVad::compute_rms(&out);

        assert!(out_rms < (in_rms * 0.35));
    }

    #[test]
    fn test_bandpass_filter_preserves_speech_core() {
        let mut filter = BandpassFilter300_3400::new();
        let speech_1000hz = generate_sine_wave(1_000.0, 16_000.0, 320, 10_000.0);
        let mut out = Vec::new();
        filter.process_buffer(&speech_1000hz, &mut out);

        let in_rms = SpectralEntropyVad::compute_rms(&speech_1000hz);
        let out_rms = SpectralEntropyVad::compute_rms(&out);

        assert!(out_rms > (in_rms * 0.5));
    }

    #[test]
    fn test_vad_detects_silence() {
        let mut vad = SpectralEntropyVad::default();
        let silence = vec![0_i16; 320];
        let media_idle = MediaPlaybackState::default();

        let res = vad.analyze_frame(&silence, &media_idle);
        assert_eq!(res.decision, VadDecision::Silence);
        assert!(!res.is_speech);
    }

    #[test]
    fn test_vad_suppresses_continuous_music_when_media_active() {
        let mut vad = SpectralEntropyVad::default();
        let music_frame = generate_sine_wave(440.0, 16_000.0, 320, 5_000.0);
        let media_active = MediaPlaybackState::new(
            true,
            "stream.tv.living_room",
            MediaStreamType::IptvLive,
            0.8,
            0.05,
        );

        let res = vad.analyze_frame(&music_frame, &media_active);
        assert!(!res.is_speech || res.decision == VadDecision::MusicOrBackground);
    }

    #[test]
    fn test_failover_device_router() {
        let mut router = FailoverDeviceRouter::default();

        let bt = AudioDevice::new(
            "dev_bt_buds",
            "device.bluetooth.buds",
            1,
            true,
            true,
            Some(85),
        );

        let builtin = AudioDevice::new(
            "dev_builtin_mic",
            "device.builtin.array",
            2,
            true,
            false,
            None,
        );

        router.register_device(bt);
        router.register_device(builtin);

        let active = router.resolve_active_device();
        assert!(active.is_some());
        assert_eq!(active.map(|d| d.id.as_str()), Some("dev_bt_buds"));

        router.update_connection_state("dev_bt_buds", false);
        let fallback = router.resolve_active_device();
        assert!(fallback.is_some());
        assert_eq!(fallback.map(|d| d.id.as_str()), Some("dev_builtin_mic"));
    }

    #[test]
    fn test_multi_mic_proximity_triage() {
        let mut triage = MultiMicTriage::default();

        let report_near = SatelliteAudioReport::new("satellite_desk", 1000, 24.5, 0.065, 0.92);

        let report_far = SatelliteAudioReport::new("satellite_kitchen", 1000, 8.0, 0.012, 0.35);

        let reports = vec![report_near, report_far];
        let winner = triage.elect_best_source(&reports);
        assert_eq!(winner, Some("satellite_desk".to_string()));
    }

    #[test]
    fn test_concurrent_pipeline_lifecycle() {
        let mut pipeline = ConcurrentAudioPipeline::<Vec<i16>>::new(16);
        let task_id = pipeline.submit(vec![1, 2, 3]);
        assert_eq!(task_id, 1);
        assert_eq!(pipeline.pending_count(), 1);

        let popped = pipeline.pop_pending();
        assert!(popped.is_some());
        if let Some(t) = popped {
            pipeline.push_completed(t);
        }

        assert_eq!(pipeline.completed_count(), 1);
        let drained = pipeline.drain_completed();
        assert_eq!(drained.len(), 1);
    }

    #[test]
    fn test_cleaner_end_to_end() {
        let mut cleaner = AudioCleaner::new();
        let frame = generate_sine_wave(1200.0, 16_000.0, 320, 8_000.0);
        let media_idle = MediaPlaybackState::default();

        let cleaned = cleaner.process_frame(&frame, &media_idle);
        assert_eq!(cleaned.frame_samples, 320);
    }
}
