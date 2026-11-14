package com.nuxiva.edge.features.audio_listener

object NativeWake {

    private val loaded: Boolean = try {
        System.loadLibrary("nuxiva_wakeword")
        true
    } catch (_: UnsatisfiedLinkError) {
        false
    }

    val isAvailable: Boolean
        get() = loaded

    external fun create(model: ByteArray, sensitivity: Float): Long

    external fun push(handle: Long, pcm: ByteArray): ByteArray?

    external fun destroy(handle: Long)
}
