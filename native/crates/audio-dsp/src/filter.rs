#[derive(Debug, Clone, PartialEq)]
pub struct BiquadSection {
    b0: f32,
    b1: f32,
    b2: f32,
    a1: f32,
    a2: f32,
    x1: f32,
    x2: f32,
    y1: f32,
    y2: f32,
}

impl BiquadSection {
    #[must_use]
    pub const fn new(b0: f32, b1: f32, b2: f32, a1: f32, a2: f32) -> Self {
        Self {
            b0,
            b1,
            b2,
            a1,
            a2,
            x1: 0.0,
            x2: 0.0,
            y1: 0.0,
            y2: 0.0,
        }
    }

    pub fn process_sample(&mut self, input: f32) -> f32 {
        let output = (self.b0 * input) + (self.b1 * self.x1) + (self.b2 * self.x2)
            - (self.a1 * self.y1)
            - (self.a2 * self.y2);

        self.x2 = self.x1;
        self.x1 = input;
        self.y2 = self.y1;
        self.y1 = output;

        output
    }

    pub fn reset(&mut self) {
        self.x1 = 0.0;
        self.x2 = 0.0;
        self.y1 = 0.0;
        self.y2 = 0.0;
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct BandpassFilter300_3400 {
    highpass_300: BiquadSection,
    lowpass_3400: BiquadSection,
}

impl Default for BandpassFilter300_3400 {
    fn default() -> Self {
        Self::new()
    }
}

impl BandpassFilter300_3400 {
    #[must_use]
    pub const fn new() -> Self {
        let highpass = BiquadSection::new(
            0.919_964_5,
            -1.839_929,
            0.919_964_5,
            -1.833_732_6,
            0.846_125_4,
        );

        let lowpass = BiquadSection::new(
            0.231_273_5,
            0.462_547,
            0.231_273_5,
            -0.282_630_1,
            0.207_724_1,
        );

        Self {
            highpass_300: highpass,
            lowpass_3400: lowpass,
        }
    }

    pub fn process_sample(&mut self, sample_f32: f32) -> f32 {
        let hp_out = self.highpass_300.process_sample(sample_f32);
        self.lowpass_3400.process_sample(hp_out)
    }

    pub fn process_buffer(&mut self, input: &[i16], output: &mut Vec<i16>) {
        output.clear();
        output.reserve(input.len());
        for &sample in input {
            let sample_f = f32::from(sample);
            let filtered = self.process_sample(sample_f);
            let clamped = filtered.clamp(-32_768.0, 32_767.0);
            #[allow(clippy::cast_possible_truncation)]
            let sample_i16 = clamped as i16;
            output.push(sample_i16);
        }
    }

    pub fn reset(&mut self) {
        self.highpass_300.reset();
        self.lowpass_3400.reset();
    }
}
