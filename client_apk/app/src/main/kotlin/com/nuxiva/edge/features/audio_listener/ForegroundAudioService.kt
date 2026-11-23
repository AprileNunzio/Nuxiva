package com.nuxiva.edge.features.audio_listener

import android.app.Notification
import android.app.Service
import android.content.Intent
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import com.nuxiva.edge.R
import com.nuxiva.edge.core.NuxivaApplication
import com.nuxiva.edge.core.graph
import com.nuxiva.edge.features.sensor_uplink.SensorUplink
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import java.io.File

class ForegroundAudioService : Service(), WakeWordDetector.WakeWordCallback {

    private val serviceJob = SupervisorJob()
    private val serviceScope = CoroutineScope(Dispatchers.IO + serviceJob)

    private val wakeDetector = WakeWordDetector()
    private var uplink: SensorUplink? = null

    private var audioRecord: AudioRecord? = null
    private var isRecording = false

    private val sampleRate = SensorUplink.VOICE_RATE
    private val channelConfig = AudioFormat.CHANNEL_IN_MONO
    private val audioFormat = AudioFormat.ENCODING_PCM_16BIT
    private val WAKE_MODEL_FILE = "wakeword.nxwk"

    override fun onCreate() {
        super.onCreate()
        wakeDetector.setCallback(this)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val wanted = intent?.getStringExtra(EXTRA_NODE_ID).orEmpty()
        val profiles = graph.profiles.profiles.value
        val profile = profiles.firstOrNull { it.nodeId == wanted } ?: profiles.firstOrNull()
        uplink = profile?.let(::SensorUplink)

        val modelFile = File(filesDir, WAKE_MODEL_FILE)
        val ready = modelFile.isFile && wakeDetector.loadModel(modelFile.readBytes()) == WakeWordDetector.State.Ready
        val notification: Notification = NotificationCompat.Builder(this, NuxivaApplication.AUDIO_CHANNEL_ID)
            .setContentTitle("Nuxiva Edge")
            .setContentText(
                when {
                    ready -> getString(R.string.wake_listening)
                    wakeDetector.state == WakeWordDetector.State.MissingLibrary -> getString(R.string.wake_missing_library)
                    wakeDetector.state == WakeWordDetector.State.InvalidModel -> getString(R.string.wake_invalid_model)
                    else -> getString(R.string.wake_missing_model)
                }
            )
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setOngoing(true)
            .build()

        startForeground(1001, notification)
        if (!ready || uplink == null) {
            stopSelf()
            return START_NOT_STICKY
        }
        if (!isRecording) {
            startContinuousRecording()
        }
        return START_STICKY
    }

    private fun startContinuousRecording() {
        val bufferSize = AudioRecord.getMinBufferSize(sampleRate, channelConfig, audioFormat)
        try {
            audioRecord = AudioRecord(
                MediaRecorder.AudioSource.VOICE_RECOGNITION,
                sampleRate,
                channelConfig,
                audioFormat,
                bufferSize
            )

            audioRecord?.startRecording()
            isRecording = true
            wakeDetector.start()

            serviceScope.launch {
                val buffer = ByteArray(bufferSize)
                while (isRecording && isActive) {
                    val readBytes = audioRecord?.read(buffer, 0, buffer.size) ?: 0
                    if (readBytes > 0) {
                        wakeDetector.processAudioFrame(buffer.copyOf(readBytes))
                    }
                }
            }
        } catch (error: SecurityException) {
            Log.w(TAG, "Microphone permission missing: ${error.message}")
            stopSelf()
        }
    }

    override fun onWakeWordDetected(confidence: Float, capturedPcm: ByteArray) {
        val target = uplink ?: return
        serviceScope.launch { target.voice(capturedPcm) }
    }

    override fun onDestroy() {
        super.onDestroy()
        isRecording = false
        wakeDetector.stop()
        try {
            audioRecord?.stop()
            audioRecord?.release()
        } catch (error: IllegalStateException) {
            Log.w(TAG, "Microphone stop failed: ${error.message}")
        }
        serviceJob.cancel()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    companion object {
        const val EXTRA_NODE_ID = "NODE_ID"
        private const val TAG = "NuxivaAudio"
    }
}
