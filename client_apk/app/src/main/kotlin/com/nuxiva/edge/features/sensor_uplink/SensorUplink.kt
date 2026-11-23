package com.nuxiva.edge.features.sensor_uplink

import android.util.Base64
import android.util.Log
import com.nuxiva.edge.node.NodeFailure
import com.nuxiva.edge.node.NodeHttp
import com.nuxiva.edge.node.NodeProfile
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject

class SensorUplink(private val profile: NodeProfile) {
    private val http = NodeHttp(profile)

    suspend fun frame(jpeg: ByteArray): Boolean {
        if (jpeg.isEmpty() || jpeg.size > MAX_FRAME) return false
        val body = buildJsonObject { put("frame", JsonPrimitive(Base64.encodeToString(jpeg, Base64.NO_WRAP))) }
        return send(FRAME_PATH, body, FRAME_TIMEOUT)
    }

    suspend fun voice(pcm16: ByteArray): Boolean {
        if (pcm16.isEmpty() || pcm16.size > MAX_VOICE || pcm16.size % 2 != 0) return false
        val body = buildJsonObject {
            put("rate", JsonPrimitive(VOICE_RATE))
            put("pcm16", JsonPrimitive(Base64.encodeToString(pcm16, Base64.NO_WRAP)))
        }
        return send(VOICE_PATH, body, VOICE_TIMEOUT)
    }

    private suspend fun send(path: String, body: kotlinx.serialization.json.JsonObject, timeout: Long): Boolean =
        withContext(Dispatchers.IO) {
            try {
                http.post(path, body, timeout)
                true
            } catch (failure: NodeFailure) {
                Log.w(TAG, "Sensor upload to $path failed for ${profile.nodeId}: ${failure.code}")
                false
            }
        }

    companion object {
        const val VOICE_RATE = 16000
        private const val TAG = "NuxivaSensorUplink"
        private const val FRAME_PATH = "/api/nodes/vision/feed"
        private const val VOICE_PATH = "/api/nodes/voice"
        private const val MAX_FRAME = 1536 * 1024
        private const val MAX_VOICE = VOICE_RATE * 2 * 30
        private const val FRAME_TIMEOUT = 15L
        private const val VOICE_TIMEOUT = 240L
    }
}
