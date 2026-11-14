package com.nuxiva.edge.node

import com.nuxiva.logic.crypto.DeviceKey
import com.nuxiva.logic.crypto.Hex
import com.nuxiva.logic.crypto.RequestSigner
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
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
import javax.net.ssl.SSLException

class NodeCall internal constructor(private val call: Call) {

    fun cancel() = call.cancel()

    fun execute(): JsonObject {
        return try {
            call.execute().use { response -> parse(response) }
        } catch (error: SSLException) {
            throw NodeFailure.Pin(error.message ?: "tls")
        } catch (error: IOException) {
            throw NodeFailure.Unreachable(error.message ?: "io")
        }
    }

    private fun parse(response: okhttp3.Response): JsonObject {
        val text = readLimited(response)
        if (response.code == 401) {
            val detail = detail(text)
            if (detail.startsWith("node.error.")) throw NodeFailure.SignatureRejected(detail)
            throw NodeFailure.Unauthorized(detail.ifEmpty { "unauthorized" })
        }
        if (response.code >= 400) throw NodeFailure.Server(detail(text).ifEmpty { "http_${response.code}" }, response.code)
        if (text.isBlank()) return JsonObject(emptyMap())
        return try {
            JSON.parseToJsonElement(text).jsonObject
        } catch (_: Exception) {
            throw NodeFailure.Server("invalid_response", response.code)
        }
    }

    private fun readLimited(response: okhttp3.Response): String {
        val body = response.body ?: return ""
        val out = ByteArrayOutputStream()
        val buffer = ByteArray(8192)
        body.byteStream().use { stream ->
            while (true) {
                val read = stream.read(buffer)
                if (read < 0) break
                out.write(buffer, 0, read)
                if (out.size() > MAX_RESPONSE) throw NodeFailure.Server("response_too_large", response.code)
            }
        }
        return out.toString(Charsets.UTF_8.name())
    }

    private fun detail(text: String): String = try {
        JSON.parseToJsonElement(text).jsonObject["detail"]?.jsonPrimitive?.content.orEmpty()
    } catch (_: Exception) {
        ""
    }

    private companion object {
        const val MAX_RESPONSE = 2 shl 20
        val JSON = Json { ignoreUnknownKeys = true }
    }
}

class NodeHttp(private val profile: NodeProfile) {
    private val key = DeviceKey.fromSeed(Hex.decode(profile.seedHex))
    private val signer = RequestSigner(profile.nodeId, key)
    private val client: OkHttpClient = TlsClients.pinned(profile.caPem)

    fun prepare(path: String, body: JsonObject, readTimeoutSeconds: Long = 30): NodeCall {
        val payload = body.toString().toByteArray(Charsets.UTF_8)
        val builder = Request.Builder()
            .url(profile.server + path)
            .post(payload.toRequestBody(JSON_TYPE))
        if (profile.token.isNotEmpty()) builder.header("Authorization", "Bearer ${profile.token}")
        signer.headers("POST", path, payload).forEach { (name, value) -> builder.header(name, value) }
        val call = client.newBuilder().readTimeout(readTimeoutSeconds, TimeUnit.SECONDS).build().newCall(builder.build())
        return NodeCall(call)
    }

    fun post(path: String, body: JsonObject, readTimeoutSeconds: Long = 30): JsonObject =
        prepare(path, body, readTimeoutSeconds).execute()

    private companion object {
        val JSON_TYPE = "application/json".toMediaType()
    }
}
