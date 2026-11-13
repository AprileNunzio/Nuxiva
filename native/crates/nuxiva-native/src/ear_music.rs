use std::sync::Mutex;

use nuxiva_ear_core::MusicRoom;
use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;

type StepTuple = (bool, &'static str, bool);

fn lock_error() -> PyErr {
    PyRuntimeError::new_err("ear.music.poisoned")
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug, Default)]
pub struct RustMusicRoom {
    inner: Mutex<MusicRoom>,
}

#[pymethods]
impl RustMusicRoom {
    #[new]
    fn new() -> Self {
        Self::default()
    }

    fn join(&self) -> PyResult<Option<u32>> {
        Ok(self.inner.lock().map_err(|_| lock_error())?.join())
    }

    fn leave(&self, mic: u32) -> PyResult<&'static str> {
        Ok(self
            .inner
            .lock()
            .map_err(|_| lock_error())?
            .leave(mic)
            .code())
    }

    fn feed(
        &self,
        mic: u32,
        music: bool,
        idle: bool,
        frame_ms: u32,
        now_ms: u64,
    ) -> PyResult<StepTuple> {
        let step = self
            .inner
            .lock()
            .map_err(|_| lock_error())?
            .feed(mic, music, idle, frame_ms, now_ms);
        Ok((step.playing, step.change.code(), step.probe))
    }

    fn finish(&self, now_ms: u64, wait_ms: u64) -> PyResult<()> {
        self.inner
            .lock()
            .map_err(|_| lock_error())?
            .finish(now_ms, wait_ms);
        Ok(())
    }

    fn playing(&self) -> PyResult<bool> {
        Ok(self.inner.lock().map_err(|_| lock_error())?.playing())
    }

    fn mic_playing(&self, mic: u32) -> PyResult<bool> {
        Ok(self
            .inner
            .lock()
            .map_err(|_| lock_error())?
            .mic_playing(mic))
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustMusicRoom>()?;
    Ok(())
}
