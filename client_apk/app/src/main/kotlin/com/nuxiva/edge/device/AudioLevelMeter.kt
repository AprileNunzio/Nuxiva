package com.nuxiva.edge.device

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.SystemClock
import androidx.core.content.ContextCompat
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlin.math.log10
import kotlin.math.sqrt

data class AudioReading(val level: Float, val speech: Float, val atMillis: Long)

class AudioLevelMeter(private val context: Context) {
    private val state = MutableStateFlow<AudioReading?>(null)
    private var scope: CoroutineScope? = null
    private var job: Job? = null

    val reading: StateFlow<AudioReading?> = state.asStateFlow()

    @Synchronized
    fun start() {
        if (job?.isActive == true) return
        if (ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) return
        val created = CoroutineScope(SupervisorJob() + Dispatchers.IO)
        scope = created
        job = created.launch { capture() }
    }

    @Synchronized
    fun stop() {
        scope?.cancel()
        scope = null
        job = null
        state.value = null
    }

    fun fresh(maxAgeMillis: Long = FRESH_MILLIS): AudioReading? =
        state.value?.takeIf { SystemClock.elapsedRealtime() - it.atMillis <= maxAgeMillis }

    private suspend fun capture() {
        val minimum = AudioRecord.getMinBufferSize(RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
        if (minimum <= 0) return
        val recorder = try {
            AudioRecord(MediaRecorder.AudioSource.MIC, RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, minimum * 2)
        } catch (ignored: SecurityException) {
            return
        } catch (ignored: IllegalArgumentException) {
            return
        }
        if (recorder.state != AudioRecord.STATE_INITIALIZED) {
            recorder.release()
            return
        }
        val buffer = ShortArray(RATE / 10)
        var floorDb = INITIAL_FLOOR_DB
        var smooth = 0f
        try {
            recorder.startRecording()
            while (currentCoroutineContext().isActive) {
                val read = recorder.read(buffer, 0, buffer.size)
                if (read <= 0) continue
                var sum = 0.0
                for (index in 0 until read) {
                    val sample = buffer[index] / FULL_SCALE
                    sum += sample * sample
                }
                val db = 20.0 * log10(sqrt(sum / read).coerceAtLeast(MIN_RMS))
                floorDb = if (db < floorDb) db else floorDb + (db - floorDb) * FLOOR_RISE
                val level = ((db - SILENCE_DB) / (0.0 - SILENCE_DB)).coerceIn(0.0, 1.0).toFloat()
                smooth += (level - smooth) * SMOOTHING
                val speech = ((db - floorDb - SPEECH_MARGIN_DB) / SPEECH_RANGE_DB).coerceIn(0.0, 1.0).toFloat()
                state.value = AudioReading(smooth, speech, SystemClock.elapsedRealtime())
            }
        } catch (ignored: IllegalStateException) {
            return
        } finally {
            runCatching { recorder.stop() }
            recorder.release()
        }
    }

    private companion object {
        const val RATE = 16_000
        const val FULL_SCALE = 32768.0
        const val MIN_RMS = 1e-5
        const val SILENCE_DB = -70.0
        const val INITIAL_FLOOR_DB = -50.0
        const val FLOOR_RISE = 0.01
        const val SPEECH_MARGIN_DB = 6.0
        const val SPEECH_RANGE_DB = 14.0
        const val SMOOTHING = 0.5f
        const val FRESH_MILLIS = 15_000L
    }
}
