package com.nuxiva.logic.enroll

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.longOrNull
import java.net.URI
import java.util.Base64

public data class EnrollmentPayload(
    val server: String,
    val token: String,
    val pin: String,
    val expires: Long,
)

public class EnrollmentException(public val code: String) : Exception(code)

public object EnrollmentParser {
    public const val SCHEME: String = "nuxiva"
    public const val HOST: String = "enroll"
    public const val PARAMETER: String = "d"
    private const val LIMIT = 4096
    private const val LINK_LIMIT = 8192
    private val tokenPattern = Regex("[A-Za-z0-9_\\-]{20,128}")
    private val pinPattern = Regex("[0-9a-f]{64}")
    private val allowedKeys = setOf("server", "token", "pin", "expires")
    private val json = Json { isLenient = false }

    public fun parse(raw: String, nowSeconds: Long): EnrollmentPayload {
        val text = raw.trim()
        if (text.isEmpty() || text.length > LINK_LIMIT) throw EnrollmentException("enroll_file_invalid")
        val body = if (text.startsWith("$SCHEME://", ignoreCase = true)) fromLink(text) else text
        if (body.toByteArray(Charsets.UTF_8).size > LIMIT) throw EnrollmentException("enroll_file_invalid")
        val wire = try {
            json.parseToJsonElement(body) as? JsonObject
        } catch (_: Exception) {
            null
        } ?: throw EnrollmentException("enroll_file_invalid")
        if (!allowedKeys.containsAll(wire.keys)) throw EnrollmentException("enroll_file_invalid")
        val server = normalizeServer(text(wire["server"]))
        val token = text(wire["token"])
        val pin = text(wire["pin"])
        val expires = (wire["expires"] as? JsonPrimitive)?.takeIf { !it.isString }?.longOrNull
        if (token == null || !tokenPattern.matches(token) || pin == null || !pinPattern.matches(pin) || expires == null) {
            throw EnrollmentException("enroll_file_invalid")
        }
        if (expires < nowSeconds) throw EnrollmentException("enroll_file_expired")
        return EnrollmentPayload(server, token, pin, expires)
    }

    private fun text(element: kotlinx.serialization.json.JsonElement?): String? =
        (element as? JsonPrimitive)?.takeIf { it.isString }?.content

    public fun normalizeServer(value: String?): String {
        val uri = try {
            URI(value ?: throw EnrollmentException("enroll_file_invalid"))
        } catch (_: java.net.URISyntaxException) {
            throw EnrollmentException("enroll_file_invalid")
        }
        val host = uri.host
        val path = uri.rawPath.orEmpty()
        val valid = uri.scheme == "https" && !host.isNullOrEmpty() && uri.userInfo == null && uri.rawQuery == null &&
            uri.rawFragment == null && (path.isEmpty() || path == "/")
        if (!valid) throw EnrollmentException("enroll_file_invalid")
        val port = uri.port
        return if (port == -1 || port == 443) "https://$host" else "https://$host:$port"
    }

    private fun fromLink(link: String): String {
        val uri = try {
            URI(link)
        } catch (_: java.net.URISyntaxException) {
            throw EnrollmentException("enroll_file_invalid")
        }
        if (!uri.scheme.equals(SCHEME, ignoreCase = true) || !uri.host.equals(HOST, ignoreCase = true)) {
            throw EnrollmentException("enroll_file_invalid")
        }
        val encoded = uri.rawQuery.orEmpty().split('&')
            .map { it.substringBefore('=') to it.substringAfter('=', "") }
            .firstOrNull { it.first == PARAMETER }?.second
            ?: throw EnrollmentException("enroll_file_invalid")
        return try {
            String(Base64.getUrlDecoder().decode(encoded), Charsets.UTF_8)
        } catch (_: IllegalArgumentException) {
            throw EnrollmentException("enroll_file_invalid")
        }
    }
}
