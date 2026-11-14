package com.nuxiva.edge.compute

import android.util.Log
import com.nuxiva.edge.device.PowerMonitor
import com.nuxiva.edge.node.NodeFailure
import com.nuxiva.edge.node.NodeHttp
import com.nuxiva.logic.compute.ComputeJob
import com.nuxiva.logic.compute.JobCodec
import com.nuxiva.logic.compute.JobRejected
import com.nuxiva.logic.compute.ShareDecision
import com.nuxiva.logic.compute.SharePolicy
import com.nuxiva.logic.compute.ShareSettings
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.Call
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger

class ComputeRelay(
    private val http: NodeHttp,
    private val settings: () -> ShareSettings,
    private val power: PowerMonitor,
    private val ollama: OllamaProbe,
) {
    private val upstream = OkHttpClient.Builder()
        .connectTimeout(3, TimeUnit.SECONDS)
        .readTimeout(UPSTREAM_TIMEOUT_SECONDS, TimeUnit.SECONDS)
        .followRedirects(false)
        .build()

    fun decision(): ShareDecision = SharePolicy.decide(settings(), power.snapshot())

    fun sharing(): Boolean = decision() == ShareDecision.Allowed && ollama.read().available

    suspend fun run() = coroutineScope {
        val active = AtomicInteger(0)
        while (currentCoroutineContext().isActive) {
            val free = (settings().jobLimit - active.get()).coerceAtLeast(0)
            if (!withContext(Dispatchers.IO) { sharing() }) {
                delay(RETRY_MILLIS)
                continue
            }
            if (free == 0) {
                delay(ACTIVITY_MILLIS)
                continue
            }
            try {
                val reply = withContext(Dispatchers.IO) {
                    http.prepare("/api/nodes/compute/next?capacity=$free", JsonObject(emptyMap()), POLL_TIMEOUT_SECONDS).execute()
                }
                val jobs = (reply["jobs"] as? JsonArray).orEmpty().take(free)
                jobs.forEach { raw ->
                    active.incrementAndGet()
                    launch(Dispatchers.IO) {
                        try {
                            execute(raw)
                        } catch (failure: CancellationException) {
                            throw failure
                        } catch (failure: Exception) {
                            Log.e(TAG, "Compute job failed", failure)
                        } finally {
                            active.decrementAndGet()
                        }
                    }
                }
            } catch (error: CancellationException) {
                throw error
            } catch (error: NodeFailure.Unauthorized) {
                Log.w(TAG, "Compute channel stopped: node no longer authorised")
                return@coroutineScope
            } catch (error: NodeFailure) {
                Log.d(TAG, "Compute channel unavailable: ${error.code}")
                delay(RETRY_MILLIS)
            }
        }
    }

    private suspend fun execute(raw: kotlinx.serialization.json.JsonElement) {
        val item = raw as? JsonObject
        val id = item?.get("id")?.jsonPrimitive?.contentOrNull.orEmpty()
        val job = try {
            JobCodec.decode(id, item?.get("method")?.jsonPrimitive?.contentOrNull, item?.get("path")?.jsonPrimitive?.contentOrNull, item?.get("body")?.jsonPrimitive?.contentOrNull)
        } catch (rejected: JobRejected) {
            if (id.isNotEmpty()) report(id, error = rejected.code)
            return
        }
        if (!sharing()) {
            report(job.id, error = "compute_unavailable")
            return
        }
        stream(job)
    }

    private suspend fun stream(job: ComputeJob) {
        coroutineScope {
            val request = Request.Builder().url("http://${OllamaProbe.HOST}:${OllamaProbe.PORT}${job.path}")
                .method(job.method, if (job.method == "POST") job.body.toRequestBody(JSON_TYPE) else null)
                .build()
            val call: Call = upstream.newCall(request)
            val interrupted = AtomicBoolean(false)
            val watchdog = launch(Dispatchers.IO) {
                while (currentCoroutineContext().isActive) {
                    delay(ACTIVITY_MILLIS)
                    if (!sharing()) {
                        interrupted.set(true)
                        call.cancel()
                        return@launch
                    }
                }
            }
            try {
                call.execute().use { response ->
                    pump(job.id, response, interrupted)
                }
            } catch (error: IOException) {
                if (interrupted.get()) {
                    report(job.id, error = "compute_unavailable")
                } else {
                    Log.w(TAG, "Local Ollama did not answer", error)
                    report(job.id, error = "compute_ollama_unreachable")
                }
            } finally {
                watchdog.cancel()
                call.cancel()
            }
        }
    }

    private fun pump(id: String, response: okhttp3.Response, interrupted: AtomicBoolean) {
        val status = response.code
        val contentType = response.header("Content-Type") ?: "application/json"
        val stream = response.body?.byteStream()
        val chunk = ByteArray(READ_SIZE)
        val buffer = ByteArrayOutputStream()
        var last = System.nanoTime()
        var first = true
        while (true) {
            val read = stream?.read(chunk) ?: -1
            if (interrupted.get()) {
                report(id, error = "compute_unavailable")
                return
            }
            if (read > 0) buffer.write(chunk, 0, read)
            val ended = read < 0
            val due = first || ended || buffer.size() >= FLUSH_BYTES || System.nanoTime() - last >= FLUSH_NANOS
            if (due && (buffer.size() > 0 || ended || first)) {
                val cancel = report(id, buffer.toByteArray(), if (first) status else null, if (first) contentType else "", ended)
                buffer.reset()
                last = System.nanoTime()
                first = false
                if (cancel || ended) return
            }
        }
    }

    private fun report(id: String, data: ByteArray = ByteArray(0), status: Int? = null, contentType: String = "", done: Boolean = false, error: String = ""): Boolean {
        val body = JobCodec.chunk(id, data, status, contentType, done, error)
        return try {
            http.post("/api/nodes/compute/chunk", body).get("cancel")?.jsonPrimitive?.contentOrNull == "true"
        } catch (failure: NodeFailure) {
            Log.w(TAG, "Compute chunk not delivered: ${failure.code}")
            true
        }
    }

    private companion object {
        const val TAG = "NuxivaCompute"
        const val READ_SIZE = 1 shl 16
        const val FLUSH_BYTES = 1 shl 14
        const val FLUSH_NANOS = 50_000_000L
        const val POLL_TIMEOUT_SECONDS = 40L
        const val UPSTREAM_TIMEOUT_SECONDS = 600L
        const val RETRY_MILLIS = 10_000L
        const val ACTIVITY_MILLIS = 500L
        val JSON_TYPE = "application/json".toMediaType()
    }
}
