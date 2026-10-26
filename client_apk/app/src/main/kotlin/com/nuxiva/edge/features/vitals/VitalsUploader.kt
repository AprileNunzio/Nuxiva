package com.nuxiva.edge.features.vitals

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class VitalsUploader(private val vault: VitalsVault) {

    private val client = OkHttpClient.Builder()
        .connectTimeout(5, TimeUnit.SECONDS)
        .readTimeout(8, TimeUnit.SECONDS)
        .build()

    fun send(samples: List<VitalSample>): Boolean {
        if (samples.isEmpty() || !vault.linked()) return true
        return samples.chunked(MAX_BATCH).all { post(it) }
    }

    private fun post(batch: List<VitalSample>): Boolean {
        val rows = JSONArray()
        batch.forEach {
            rows.put(JSONObject().put("metric", it.metric).put("value", it.value).put("ts", it.timestampSeconds))
        }
        val request = Request.Builder()
            .url("${vault.server}/api/vitals/push")
            .header("Authorization", "Bearer ${vault.token}")
            .post(JSONObject().put("samples", rows).toString().toRequestBody(JSON))
            .build()
        return runCatching { client.newCall(request).execute().use { it.isSuccessful } }.getOrDefault(false)
    }

    companion object {
        private const val MAX_BATCH = 60
        private val JSON = "application/json".toMediaType()
    }
}
