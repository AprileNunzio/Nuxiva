package com.nuxiva.logic.update

import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.longOrNull

public data class UpdateOffer(val version: String, val url: String, val sha256: String, val sizeBytes: Long?)

public enum class UpdateStep(public val wire: String) {
    Idle("idle"),
    Checking("checking"),
    Downloading("downloading"),
    Installing("installing"),
    AwaitingUser("awaiting_user"),
    Failed("failed"),
    RolledBack("rolled_back"),
}

public object UpdatePolicy {
    public const val OFFICIAL_PREFIX: String = "https://github.com/AprileNunzio/Nuxiva/releases/download/"
    public const val MAX_BYTES: Long = 200L * 1024 * 1024

    private val versionPattern = Regex("""\d{1,4}(\.\d{1,4}){1,3}""")
    private val hashPattern = Regex("""[0-9a-f]{64}""")
    private val urlPattern = Regex("""https://github\.com/AprileNunzio/Nuxiva/releases/download/[A-Za-z0-9._\-]{1,64}/Nuxiva(_Node)?\.apk""")

    public fun parse(element: JsonElement?): UpdateOffer? {
        val obj = element as? JsonObject ?: return null
        val version = text(obj["version"])?.removePrefix("v") ?: return null
        val url = text(obj["url"]) ?: return null
        val hash = text(obj["sha256"])?.lowercase() ?: return null
        if (!versionPattern.matches(version) || !hashPattern.matches(hash)) return null
        if (!urlPattern.matches(url) || !url.startsWith(OFFICIAL_PREFIX)) return null
        val size = (obj["size"] as? JsonPrimitive)?.longOrNull?.takeIf { it in 1..MAX_BYTES }
        return UpdateOffer(version, url, hash, size)
    }

    public fun isNewer(candidate: String, current: String): Boolean {
        val a = numbers(candidate) ?: return false
        val b = numbers(current) ?: return false
        for (index in 0 until maxOf(a.size, b.size)) {
            val left = a.getOrElse(index) { 0 }
            val right = b.getOrElse(index) { 0 }
            if (left != right) return left > right
        }
        return false
    }

    public fun safeCode(raw: String): String {
        val cleaned = raw.lowercase().replace(Regex("[^a-z0-9._-]"), "_").take(CODE_LIMIT)
        return cleaned.ifEmpty { "error" }
    }

    private fun numbers(version: String): List<Int>? {
        val trimmed = version.removePrefix("v")
        if (!versionPattern.matches(trimmed)) return null
        return trimmed.split('.').map { it.toInt() }
    }

    private fun text(element: JsonElement?): String? = (element as? JsonPrimitive)?.takeIf { it.isString }?.contentOrNull?.trim()?.takeIf { it.isNotEmpty() }

    private const val CODE_LIMIT = 48
}
