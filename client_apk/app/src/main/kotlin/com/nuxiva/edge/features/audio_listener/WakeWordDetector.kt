package com.nuxiva.edge.features.audio_listener

import java.nio.ByteBuffer
import java.nio.ByteOrder

class WakeWordDetector {

    interface WakeWordCallback {
        fun onWakeWordDetected(confidence: Float, capturedPcm: ByteArray)
    }

    enum class State { MissingLibrary, MissingModel, InvalidModel, Ready }

    private var callback: WakeWordCallback? = null
    private var handle: Long = 0L
    @Volatile
    private var isAnalyzing = false

    var state: State = if (NativeWake.isAvailable) State.MissingModel else State.MissingLibrary
        private set

    fun setCallback(cb: WakeWordCallback) {
        this.callback = cb
    }

    @Synchronized
    fun loadModel(model: ByteArray, sensitivity: Float = 1.0f): State {
        release()
        if (!NativeWake.isAvailable) {
            state = State.MissingLibrary
            return state
        }
        val created = NativeWake.create(model, sensitivity)
        if (created <= 0L) {
            state = State.InvalidModel
            return state
        }
        handle = created
        state = State.Ready
        return state
    }

    fun start() {
        isAnalyzing = state == State.Ready
    }

    fun stop() {
        isAnalyzing = false
    }

    @Synchronized
    fun release() {
        isAnalyzing = false
        if (handle > 0L) {
            NativeWake.destroy(handle)
        }
        handle = 0L
        state = if (NativeWake.isAvailable) State.MissingModel else State.MissingLibrary
    }

    @Synchronized
    fun processAudioFrame(pcmChunk: ByteArray) {
        if (!isAnalyzing || handle <= 0L || pcmChunk.size < 2) return
        val aligned = if (pcmChunk.size % 2 == 0) pcmChunk else pcmChunk.copyOf(pcmChunk.size - 1)
        val hit = NativeWake.push(handle, aligned) ?: return
        if (hit.size <= Float.SIZE_BYTES) return
        val confidence = ByteBuffer.wrap(hit, 0, Float.SIZE_BYTES).order(ByteOrder.LITTLE_ENDIAN).float
        callback?.onWakeWordDetected(confidence, hit.copyOfRange(Float.SIZE_BYTES, hit.size))
    }
}
