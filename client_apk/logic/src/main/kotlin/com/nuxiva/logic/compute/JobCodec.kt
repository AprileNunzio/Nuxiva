package com.nuxiva.logic.compute

import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import java.util.Base64

public class JobRejected(public val code: String) : Exception(code)

public class ComputeJob(
    public val id: String,
    public val method: String,
    public val path: String,
    public val body: ByteArray,
)

public object JobCodec {
    public const val BODY_LIMIT: Int = 1 shl 20
    private val allowed = setOf(
        "POST /api/chat", "POST /api/generate", "POST /api/embed", "POST /api/embeddings",
        "POST /api/show", "GET /api/tags", "GET /api/ps", "GET /api/version",
    )
    private val idPattern = Regex("[0-9a-f]{32}")

    public fun decode(id: String?, method: String?, path: String?, bodyBase64: String?): ComputeJob {
        if (id == null || !idPattern.matches(id)) throw JobRejected("compute_invalid_job")
        if ("$method $path" !in allowed) throw JobRejected("compute_path_not_allowed")
        val body = try {
            Base64.getDecoder().decode(bodyBase64.orEmpty())
        } catch (_: IllegalArgumentException) {
            throw JobRejected("compute_invalid_body")
        }
        if (body.size > BODY_LIMIT) throw JobRejected("compute_body_too_large")
        return ComputeJob(id, method.orEmpty(), path.orEmpty(), body)
    }

    public fun chunk(
        id: String,
        data: ByteArray,
        status: Int? = null,
        contentType: String = "",
        done: Boolean = false,
        error: String = "",
    ): JsonObject = buildJsonObject {
        put("id", id)
        put("data", Base64.getEncoder().encodeToString(data))
        put("done", done || error.isNotEmpty())
        if (status != null) {
            put("status", status)
            put("content_type", JsonPrimitive(contentType.take(120)))
        }
        if (error.isNotEmpty()) put("error", error.take(80))
    }
}
