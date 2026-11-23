package com.nuxiva.edge.node

import com.nuxiva.logic.crypto.DeviceKey
import com.nuxiva.logic.crypto.Hex
import com.nuxiva.logic.enroll.EnrollmentException
import com.nuxiva.logic.enroll.EnrollmentParser
import com.nuxiva.logic.enroll.EnrollmentPayload
import com.nuxiva.logic.enroll.NodeIds
import com.nuxiva.logic.net.PinnedTrust
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.IOException

class EnrollmentFailure(val code: String) : Exception(code)

class Enroller(private val store: ProfileStore) {

    suspend fun enroll(payload: EnrollmentPayload, displayName: String): NodeProfile =
        redeem(payload, android.os.Build.MODEL.orEmpty(), displayName)

    suspend fun redeem(payload: EnrollmentPayload, deviceModel: String, displayName: String): NodeProfile =
        withContext(Dispatchers.IO) {
            val caPem = fetchCa(payload.server)
            val fingerprint = try {
                PinnedTrust.fingerprint(caPem)
            } catch (_: Exception) {
                throw EnrollmentFailure("enroll_ca_invalid")
            }
            if (!PinnedTrust.matches(payload.pin, fingerprint)) throw EnrollmentFailure("enroll_pin_mismatch")
            val key = DeviceKey.generate()
            val nodeId = NodeIds.generate(deviceModel)
            val name = displayName.trim().take(NAME_LIMIT).ifEmpty { nodeId }
            val bootstrap = NodeProfile(nodeId, name, payload.server, "", caPem, fingerprint, Hex.encode(key.seedBytes()), System.currentTimeMillis() / 1000L, peerId = payload.peer)
            val body = buildJsonObject {
                put("token", JsonPrimitive(payload.token))
                put("id", JsonPrimitive(nodeId))
                put("name", JsonPrimitive(name))
                put("type", JsonPrimitive("android"))
                put("pubkey", JsonPrimitive(key.publicHex()))
            }
            val reply = try {
                NodeHttp(bootstrap).post("/api/nodes/enroll", body)
            } catch (failure: NodeFailure.Server) {
                throw EnrollmentFailure(failure.code)
            } catch (failure: NodeFailure.Pin) {
                throw EnrollmentFailure("enroll_pin_mismatch")
            } catch (failure: NodeFailure) {
                throw EnrollmentFailure("enroll_unreachable")
            }
            val token = reply["token"]?.jsonPrimitive?.content.orEmpty()
            if (token.isEmpty()) throw EnrollmentFailure("enroll_rejected")
            val announced = reply["peer"]?.jsonPrimitive?.takeIf { it.isString }?.content.orEmpty()
            val peerId = payload.peer.ifEmpty { if (PEER_ID.matches(announced)) announced else "" }
            val profile = bootstrap.copy(token = token, peerId = peerId)
            if (!store.add(profile)) throw EnrollmentFailure("enroll_too_many_nodes")
            profile
        }

    suspend fun payloadForCode(server: String, code: String): EnrollmentPayload =
        withContext(Dispatchers.IO) {
            val body = buildJsonObject { put("code", JsonPrimitive(code)) }.toString()
                .toRequestBody("application/json".toMediaType())
            val request = Request.Builder().url("$server$CODE_PATH").post(body).build()
            val text = try {
                TlsClients.firstContact().newCall(request).execute().use { response ->
                    val bytes = response.body?.byteStream()?.use { it.readNBytesCompat(CODE_LIMIT + 1) } ?: ByteArray(0)
                    if (bytes.size > CODE_LIMIT) throw EnrollmentFailure("enroll_code_invalid")
                    when (response.code) {
                        200 -> String(bytes, Charsets.UTF_8)
                        429 -> throw EnrollmentFailure("rate_limited")
                        403 -> throw EnrollmentFailure("enroll_code_invalid")
                        else -> throw EnrollmentFailure("enroll_unreachable")
                    }
                }
            } catch (error: IOException) {
                throw EnrollmentFailure("enroll_unreachable")
            }
            val payload = try {
                EnrollmentParser.parse(text, System.currentTimeMillis() / 1000L)
            } catch (error: EnrollmentException) {
                throw EnrollmentFailure(error.code)
            }
            if (payload.server != server) throw EnrollmentFailure("enroll_file_invalid")
            payload
        }

    private fun fetchCa(server: String): String {
        val request = Request.Builder().url("$server$CA_PATH").get().build()
        return try {
            TlsClients.firstContact().newCall(request).execute().use { response ->
                if (response.code != 200) throw EnrollmentFailure("enroll_unreachable")
                val bytes = response.body?.byteStream()?.use { it.readNBytesCompat(CA_LIMIT + 1) } ?: ByteArray(0)
                if (bytes.size > CA_LIMIT) throw EnrollmentFailure("enroll_ca_invalid")
                String(bytes, Charsets.US_ASCII)
            }
        } catch (error: IOException) {
            throw EnrollmentFailure("enroll_unreachable")
        }
    }

    private fun java.io.InputStream.readNBytesCompat(limit: Int): ByteArray {
        val out = java.io.ByteArrayOutputStream()
        val buffer = ByteArray(4096)
        while (out.size() < limit) {
            val read = read(buffer, 0, minOf(buffer.size, limit - out.size()))
            if (read < 0) break
            out.write(buffer, 0, read)
        }
        return out.toByteArray()
    }

    private companion object {
        const val CA_PATH = "/nuxiva-ca.crt"
        const val CODE_PATH = "/api/android/enrollment-code"
        const val CODE_LIMIT = 8192
        const val CA_LIMIT = 65536
        const val NAME_LIMIT = 60
        val PEER_ID = Regex("[0-9a-f]{64}")
    }
}
