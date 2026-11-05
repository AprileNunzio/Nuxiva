use wasm_bindgen::prelude::*;

use crate::hands::HandsEngine;

#[wasm_bindgen]
#[derive(Debug)]
pub struct WasmHands {
    inner: HandsEngine,
}

#[wasm_bindgen]
impl WasmHands {
    #[wasm_bindgen(constructor)]
    pub fn new(profile_json: &str) -> Result<WasmHands, JsError> {
        Ok(Self {
            inner: HandsEngine::new(profile_json).map_err(|e| JsError::new(&e.to_string()))?,
        })
    }

    #[wasm_bindgen(js_name = setProfile)]
    pub fn set_profile(&mut self, profile_json: &str) -> Result<(), JsError> {
        self.inner
            .set_profile(profile_json)
            .map_err(|e| JsError::new(&e.to_string()))
    }

    #[wasm_bindgen(js_name = setScene)]
    pub fn set_scene(
        &mut self,
        faces_json: &str,
        audience: &str,
        trust_guests: bool,
    ) -> Result<(), JsError> {
        self.inner
            .set_scene(faces_json, audience, trust_guests)
            .map_err(|e| JsError::new(&e.to_string()))
    }

    pub fn feed(&mut self, frame_json: &str, context: &str) -> Result<String, JsError> {
        self.inner
            .feed_json(frame_json, context)
            .map_err(|e| JsError::new(&e.to_string()))
    }

    #[wasm_bindgen(js_name = trustedHands)]
    #[must_use]
    pub fn trusted_hands(&self) -> usize {
        self.inner.tally().trusted
    }
}
