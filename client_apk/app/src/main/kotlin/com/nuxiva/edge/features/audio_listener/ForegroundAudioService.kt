package com.nuxiva.edge.features.audio_listener

import android.app.Notification
import android.app.Service
import android.content.Intent
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.IBinder
import androidx.core.app.NotificationCompat
import com.nuxiva.edge.core.NuxivaApplication
import kotlinx.coroutines.*
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.File
import com.nuxiva.edge.R

class ForegroundAudioService : Service(), WakeWordDetector.WakeWordCallback {

    private val serviceJob = SupervisorJob()
    private val serviceScope = CoroutineScope(Dispatchers.IO + serviceJob)

    private val wakeDetector = WakeWordDetector()
    private val httpClient = OkHttpClient()

    private var audioRecord: AudioRecord? = null
    private var isRecording = false

    private val sampleRate = 16000
    private val channelConfig = AudioFormat.CHANNEL_IN_MONO
    private val audioFormat = AudioFormat.ENCODING_PCM_16BIT
    private val WAKE_MODEL_FILE = "wakeword.nxwk"
    private var serverUrl = "http://192.168.1.100:8443/api/v1/command"

    override fun onCreate() {
        super.onCreate()
        wakeDetector.setCallback(this)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        intent?.getStringExtra("SERVER_URL")?.let {
            if (it.isNotEmpty()) {
                serverUrl = "$it/api/v1/command"
            }
        }

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
        if (!ready) {
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
        } catch (_: SecurityException) {
            stopSelf()
        }
    }

    override fun onWakeWordDetected(confidence: Float, capturedPcm: ByteArray) {
        serviceScope.launch {
            val json = JSONObject().apply {
                put("query", "")
                put("wake_confidence", confidence.toDouble())
                put("device_id", "apk_edge_tablet_phone")
                put("voice_pcm_base64", android.util.Base64.encodeToString(capturedPcm, android.util.Base64.NO_WRAP))
            }
            val body = json.toString().toRequestBody("application/json".toMediaType())
            val request = Request.Builder()
                .url(serverUrl)
                .addHeader("Authorization", "Bearer v1.local.apk_edge_token")
                .post(body)
                .build()

            try {
                httpClient.newCall(request).execute().close()
            } catch (_: Exception) {
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        isRecording = false
        wakeDetector.stop()
        try {
            audioRecord?.stop()
            audioRecord?.release()
        } catch (_: Exception) {
        }
        serviceJob.cancel()
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
