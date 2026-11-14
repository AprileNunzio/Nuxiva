#![allow(unsafe_code)]

use jni::JNIEnv;
use jni::objects::{JByteArray, JClass};
use jni::sys::{jbyteArray, jfloat, jlong};
use nuxiva_wakeword_core::handle;

fn handle_of(value: jlong) -> Option<u64> {
    u64::try_from(value).ok().filter(|v| *v > 0)
}

#[unsafe(no_mangle)]
pub extern "system" fn Java_com_nuxiva_edge_features_audio_1listener_NativeWake_create<'local>(
    env: JNIEnv<'local>,
    _class: JClass<'local>,
    model: JByteArray<'local>,
    sensitivity: jfloat,
) -> jlong {
    let Ok(bytes) = env.convert_byte_array(&model) else {
        return 0;
    };
    handle::create(&bytes, sensitivity)
        .ok()
        .and_then(|id| jlong::try_from(id).ok())
        .unwrap_or(0)
}

#[unsafe(no_mangle)]
pub extern "system" fn Java_com_nuxiva_edge_features_audio_1listener_NativeWake_push<'local>(
    env: JNIEnv<'local>,
    _class: JClass<'local>,
    handle_value: jlong,
    pcm: JByteArray<'local>,
) -> jbyteArray {
    let null = std::ptr::null_mut();
    let Some(id) = handle_of(handle_value) else {
        return null;
    };
    let Ok(bytes) = env.convert_byte_array(&pcm) else {
        return null;
    };
    let Ok(hits) = handle::push(id, &bytes) else {
        return null;
    };
    let Some(best) = hits
        .iter()
        .max_by(|a, b| a.confidence.total_cmp(&b.confidence))
    else {
        return null;
    };
    env.byte_array_from_slice(&handle::encode(best))
        .map_or(null, JByteArray::into_raw)
}

#[unsafe(no_mangle)]
pub extern "system" fn Java_com_nuxiva_edge_features_audio_1listener_NativeWake_destroy<'local>(
    _env: JNIEnv<'local>,
    _class: JClass<'local>,
    handle_value: jlong,
) {
    if let Some(id) = handle_of(handle_value) {
        handle::destroy(id);
    }
}
