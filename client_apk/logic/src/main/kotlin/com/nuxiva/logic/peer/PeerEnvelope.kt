package com.nuxiva.logic.peer

import com.nuxiva.logic.crypto.Hex
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.longOrNull
import org.bouncycastle.crypto.params.Ed25519PublicKeyParameters
import org.bouncycastle.crypto.signers.Ed25519Signer
import java.security.MessageDigest

public class PeerException(public val code: String) : Exception(code)

public data class Locate(val sender: String, val seq: Long, val ts: Long, val addrs: List<String>)

public object PeerEnvelope {
    public const val DOMAIN: String = "nuxiva-peer-v1"
    public const val MAX_PAYLOAD: Int = 16 * 1024
    public const val MAX_TTL: Long = 12
    public const val MAX_ADDRS: Int = 8
    public const val MAX_DATAGRAM: Int = 1200
    private val fields = setOf("from", "seq", "ts", "ttl", "payload", "sig")
    private val idPattern = Regex("[0-9a-f]{64}")
    private val sigPattern = Regex("[0-9a-f]{128}")
    private val json = Json { isLenient = false }

    private fun fail(code: String): PeerException = PeerException("peer.error.$code")

    public fun signedBytes(sender: String, seq: Long, ts: Long, payload: String): ByteArray {
        val digest = Hex.encode(MessageDigest.getInstance("SHA-256").digest(payload.toByteArray(Charsets.UTF_8)))
        return "$DOMAIN\n$sender\n$seq\n$ts\n$digest".toByteArray(Charsets.UTF_8)
    }

    public fun verifyLocate(raw: String, trusted: Set<String>): Locate {
        val envelope = parseObject(raw) ?: throw fail("payload")
        if (envelope.keys != fields) throw fail("payload")
        val sender = text(envelope["from"])
        val payload = text(envelope["payload"])
        val sig = text(envelope["sig"])
        val seq = integer(envelope["seq"])
        val ts = integer(envelope["ts"])
        val ttl = integer(envelope["ttl"])
        if (payload == null || seq == null || ts == null || ttl == null || seq < 0 || ttl < 0) throw fail("payload")
        if (payload.toByteArray(Charsets.UTF_8).size > MAX_PAYLOAD || ttl > MAX_TTL) throw fail("limit")
        if (sender == null || sender !in trusted || !idPattern.matches(sender)) throw fail("untrusted")
        if (sig == null || !sigPattern.matches(sig)) throw fail("signature")
        if (!verified(sender, sig, signedBytes(sender, seq, ts, payload))) throw fail("signature")
        val message = parseObject(payload) ?: throw fail("payload")
        if (message.keys != setOf("type", "addrs") || text(message["type"]) != "locate") throw fail("payload")
        return Locate(sender, seq, ts, addresses(message["addrs"]))
    }

    private fun verified(sender: String, sig: String, message: ByteArray): Boolean = try {
        val signer = Ed25519Signer()
        signer.init(false, Ed25519PublicKeyParameters(Hex.decode(sender), 0))
        signer.update(message, 0, message.size)
        signer.verifySignature(Hex.decode(sig))
    } catch (_: RuntimeException) {
        false
    }

    private fun addresses(element: JsonElement?): List<String> {
        val array = element as? JsonArray ?: throw fail("limit")
        if (array.isEmpty() || array.size > MAX_ADDRS) throw fail("limit")
        val out = array.map { text(it) ?: throw fail("field") }
        if (!out.all(PeerAddress::check)) throw fail("field")
        if (out.toSet().size != out.size) throw fail("field")
        return out
    }

    private fun parseObject(raw: String): JsonObject? = try {
        json.parseToJsonElement(raw) as? JsonObject
    } catch (_: Exception) {
        null
    }

    private fun text(element: JsonElement?): String? = (element as? JsonPrimitive)?.takeIf { it.isString }?.content

    private fun integer(element: JsonElement?): Long? = (element as? JsonPrimitive)?.takeIf { !it.isString }?.longOrNull
}
