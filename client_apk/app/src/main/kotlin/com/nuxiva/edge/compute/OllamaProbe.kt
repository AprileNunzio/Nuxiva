package com.nuxiva.edge.compute

import android.util.Log
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.IOException
import java.util.concurrent.TimeUnit

data class OllamaModel(val name: String, val sizeGb: Double)

data class OllamaState(
    val available: Boolean,
    val version: String,
    val models: List<OllamaModel>,
    val running: List<OllamaModel>,
) {
    companion object {
        val Absent = OllamaState(false, "", emptyList(), emptyList())
    }
}

class OllamaProbe {
    private val client = OkHttpClient.Builder()
        .connectTimeout(TIMEOUT_SECONDS, TimeUnit.SECONDS)
        .readTimeout(TIMEOUT_SECONDS, TimeUnit.SECONDS)
        .followRedirects(false)
        .build()
    private var cache = OllamaState.Absent
    private var cachedAt = 0L

    @Synchronized
    fun read(force: Boolean = false): OllamaState {
        val now = System.nanoTime()
        if (!force && cachedAt != 0L && now - cachedAt < CACHE_NANOS) return cache
        val version = get("/api/version")
        cache = if (version == null) {
            OllamaState.Absent
        } else {
            OllamaState(true, version["version"]?.jsonPrimitive?.contentOrNull.orEmpty(), models(get("/api/tags")), models(get("/api/ps")))
        }
        cachedAt = now
        return cache
    }

    private fun get(path: String): JsonObject? {
        val request = Request.Builder().url("http://$HOST:$PORT$path").get().build()
        return try {
            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) return null
                val text = response.body?.source()?.let { source ->
                    source.request(LIMIT)
                    source.buffer.readUtf8(minOf(source.buffer.size, LIMIT))
                } ?: return null
                JSON.parseToJsonElement(text).jsonObject
            }
        } catch (_: java.net.ConnectException) {
            null
        } catch (error: IOException) {
            Log.d(TAG, "Local Ollama unreadable at $path", error)
            null
        } catch (error: IllegalArgumentException) {
            Log.d(TAG, "Local Ollama returned invalid JSON at $path", error)
            null
        }
    }

    private fun models(payload: JsonObject?): List<OllamaModel> {
        val items = (payload?.get("models") as? JsonArray) ?: return emptyList()
        return items.mapNotNull { element ->
            val item = element as? JsonObject ?: return@mapNotNull null
            val name = item["name"]?.jsonPrimitive?.contentOrNull ?: return@mapNotNull null
            val size = item["size"]?.jsonPrimitive?.doubleOrNull ?: 0.0
            OllamaModel(name, Math.round(size / GIB * 100.0) / 100.0)
        }
    }

    companion object {
        const val HOST = "127.0.0.1"
        const val PORT = 11434
        private const val TAG = "NuxivaOllama"
        private const val TIMEOUT_SECONDS = 2L
        private const val CACHE_NANOS = 20_000_000_000L
        private const val LIMIT = 1L shl 20
        private const val GIB = 1024.0 * 1024.0 * 1024.0
        private val JSON = Json { ignoreUnknownKeys = true }
    }
}
