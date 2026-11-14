package com.nuxiva.logic.enroll

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.doubleOrNull
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
    private val serverPattern = Regex("(?i)https://((?:[a-z0-9_](?:[a-z0-9_\\-]*[a-z0-9_])?\\.?)+|\\[[0-9a-f:.]+\\])(?::([0-9]{1,5}))?/?")
    private val base64Pattern = Regex("[A-Za-z0-9_\\-]+")
    private val pinPattern = Regex("[0-9a-f]{64}")
    private val json = Json { isLenient = false }

    public fun parse(raw: String, nowSeconds: Long): EnrollmentPayload {
        val text = raw.filterNot { it.isWhitespace() || it == '\u200b' || it == '\ufeff' }.removeSurrounding("\"").removeSurrounding("'")
        if (text.isEmpty() || text.length > LINK_LIMIT) throw EnrollmentException("enroll_file_invalid")
        val body = when {
            text.startsWith("$SCHEME://", ignoreCase = true) -> fromLink(text)
            text.startsWith("{") -> raw.trim()
            else -> decode(text)
        }
        if (body.toByteArray(Charsets.UTF_8).size > LIMIT) throw EnrollmentException("enroll_file_invalid")
        val wire = try {
            json.parseToJsonElement(body) as? JsonObject
        } catch (_: Exception) {
            null
        } ?: throw EnrollmentException("enroll_file_invalid")
        val server = normalizeServer(text(wire["server"]))
        val token = text(wire["token"])
        val pin = text(wire["pin"])
        val expires = (wire["expires"] as? JsonPrimitive)?.takeIf { !it.isString }?.let { it.longOrNull ?: it.doubleOrNull?.toLong() }
        if (token == null || !tokenPattern.matches(token) || pin == null || !pinPattern.matches(pin) || expires == null) {
            throw EnrollmentException("enroll_file_invalid")
        }
        if (expires < nowSeconds) throw EnrollmentException("enroll_file_expired")
        return EnrollmentPayload(server, token, pin, expires)
    }

    private fun text(element: kotlinx.serialization.json.JsonElement?): String? =
        (element as? JsonPrimitive)?.takeIf { it.isString }?.content

    public fun normalizeServer(value: String?): String {
        val match = serverPattern.matchEntire(value?.trim().orEmpty()) ?: throw EnrollmentException("enroll_file_invalid")
        val host = match.groupValues[1]
        val port = match.groupValues[2].takeIf { it.isNotEmpty() }?.toIntOrNull()
        if (port != null && port !in 1..65535) throw EnrollmentException("enroll_file_invalid")
        return if (port == null || port == 443) "https://$host" else "https://$host:$port"
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
        return decode(java.net.URLDecoder.decode(encoded.replace("+", "%2B"), Charsets.UTF_8))
    }

    private fun decode(encoded: String): String {
        val clean = encoded.trimEnd('=')
        if (clean.isEmpty() || !base64Pattern.matches(clean)) throw EnrollmentException("enroll_file_invalid")
        return try {
            String(Base64.getUrlDecoder().decode(clean), Charsets.UTF_8)
        } catch (_: IllegalArgumentException) {
            throw EnrollmentException("enroll_file_invalid")
        }
    }
}
