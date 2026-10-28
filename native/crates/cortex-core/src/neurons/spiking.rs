#[derive(Debug, Clone, PartialEq)]
pub struct CompartmentInput {
    pub proximal: f64,
    pub distal: f64,
    pub apical: f64,
}

impl Default for CompartmentInput {
    fn default() -> Self {
        Self {
            proximal: 0.0,
            distal: 0.0,
            apical: 0.0,
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct IzhikevichParams {
    pub a: f64,
    pub b: f64,
    pub c: f64,
    pub d: f64,
    pub v_thresh: f64,
    pub dt: f64,
}

impl Default for IzhikevichParams {
    fn default() -> Self {
        Self {
            a: 0.02,
            b: 0.2,
            c: -65.0,
            d: 8.0,
            v_thresh: 30.0,
            dt: 0.5,
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct SpikingNeuronState {
    pub v: f64,
    pub u: f64,
    pub is_spiking: bool,
    pub predictive_depolarization: f64,
    pub prediction_error: f64,
}

#[derive(Debug, Clone)]
pub struct AdaptiveSpikingNeuron {
    params: IzhikevichParams,
    state: SpikingNeuronState,
}

impl Default for AdaptiveSpikingNeuron {
    fn default() -> Self {
        Self::new(IzhikevichParams::default())
    }
}

impl AdaptiveSpikingNeuron {
    #[must_use]
    pub fn new(params: IzhikevichParams) -> Self {
        let initial_v = params.c;
        let initial_u = params.b * initial_v;
        Self {
            params,
            state: SpikingNeuronState {
                v: initial_v,
                u: initial_u,
                is_spiking: false,
                predictive_depolarization: 0.0,
                prediction_error: 0.0,
            },
        }
    }

    #[must_use]
    pub fn state(&self) -> &SpikingNeuronState {
        &self.state
    }

    pub fn reset(&mut self) {
        self.state.v = self.params.c;
        self.state.u = self.params.b * self.params.c;
        self.state.is_spiking = false;
        self.state.predictive_depolarization = 0.0;
        self.state.prediction_error = 0.0;
    }

    pub fn step(&mut self, input: &CompartmentInput) -> bool {
        if self.state.is_spiking {
            self.state.v = self.params.c;
            self.state.u += self.params.d;
            self.state.is_spiking = false;
        }

        let pred_mod = (input.distal + 0.5 * input.apical).clamp(0.0, 10.0);
        self.state.predictive_depolarization = pred_mod;

        let total_i = input.proximal + pred_mod;
        let v = self.state.v;
        let u = self.state.u;
        let dt = self.params.dt;

        let dv = dt * (0.04 * v * v + 5.0 * v + 140.0 - u + total_i);
        let du = dt * (self.params.a * (self.params.b * v - u));

        let next_v = v + dv;
        let next_u = u + du;

        if next_v >= self.params.v_thresh {
            self.state.v = self.params.v_thresh;
            self.state.u = next_u;
            self.state.is_spiking = true;
            self.state.prediction_error = (input.proximal - pred_mod).max(0.0);
        } else {
            self.state.v = next_v;
            self.state.u = next_u;
            self.state.is_spiking = false;
            self.state.prediction_error = 0.0;
        }

        self.state.is_spiking
    }
}
