package com.nuxiva.logic.peer

import com.nuxiva.logic.crypto.Hex
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.longOrNull
import kotlinx.serialization.json.put
import org.bouncycastle.crypto.params.Ed25519PublicKeyParameters
import org.bouncycastle.crypto.signers.Ed25519Signer
import java.nio.ByteBuffer
import java.security.MessageDigest

public class LedgerException(public val name: String) : Exception("ledger.error.$name") {
    public val code: String = "ledger.error.$name"
}

public data class LedgerBlock(
    val author: String,
    val index: Long,
    val prev: String,
    val ts: Long,
    val addrs: List<String>,
    val sig: String,
)

public data class LedgerHead(val author: String, val index: Long, val hash: String)

public object LedgerRules {
    public const val DOMAIN: String = "nuxiva-ledger-v1"
    public const val MAX_BLOCKS: Int = 64
    public const val SKEW_MILLIS: Long = 60_000L
    public const val MAX_AUTHORS: Int = 256
    public const val MAX_SYNC: Int = 64
    public const val MAX_WIRE: Int = 64 * 1024
    public const val MAX_FILE: Int = 16 * 1024 * 1024
    public const val MAX_TRUSTED: Int = 256
    public val GENESIS: String = "0".repeat(64)
    private val hash = Regex("[0-9a-f]{64}")
    private val signature = Regex("[0-9a-f]{128}")
    private val blockFields = setOf("author", "index", "prev", "ts", "addrs", "sig")
    private val headFields = setOf("author", "index", "hash")
    private val weak = listOf(
        "0100000000000000000000000000000000000000000000000000000000000000",
        "ecffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff7f",
        "0000000000000000000000000000000000000000000000000000000000000000",
        "0000000000000000000000000000000000000000000000000000000000000080",
        "c7176a703d4dd84fba3c0b760d10670f2a2053fa2c39ccc64ec7fd7792ac037a",
        "c7176a703d4dd84fba3c0b760d10670f2a2053fa2c39ccc64ec7fd7792ac03fa",
        "26e8958fc2b227b045c3f489f2ef98f0d5dfac05d3c63339b13802886d53fc05",
        "26e8958fc2b227b045c3f489f2ef98f0d5dfac05d3c63339b13802886d53fc85",
    ).toSet()

    public fun fail(name: String): LedgerException = LedgerException(name)

    public fun reconnectDelayMillis(attempt: Int, jitter: Long): Long {
        val base = minOf(1_000L * (1L shl attempt.coerceIn(0, 16)), 60_000L)
        return base + Math.floorMod(jitter, maxOf(base / 4, 1L))
    }

    public fun checkId(value: String) {
        if (!hash.matches(value) || value in weak) throw fail("field")
    }

    internal fun isHash(value: String): Boolean = hash.matches(value)

    private fun longBytes(value: Long): ByteArray = ByteBuffer.allocate(8).putLong(value).array()

    public fun addrsDigest(addrs: List<String>): String {
        val digest = MessageDigest.getInstance("SHA-256")
        digest.update(longBytes(addrs.size.toLong()))
        for (addr in addrs) {
            val raw = addr.toByteArray(Charsets.UTF_8)
            digest.update(longBytes(raw.size.toLong()))
            digest.update(raw)
        }
        return Hex.encode(digest.digest())
    }

    public fun signedBytes(author: String, index: Long, prev: String, ts: Long, addrs: List<String>): ByteArray =
        "$DOMAIN\n$author\n$index\n$prev\n$ts\n${addrsDigest(addrs)}".toByteArray(Charsets.UTF_8)

    public fun hash(block: LedgerBlock): String {
        val digest = MessageDigest.getInstance("SHA-256")
        digest.update(signedBytes(block.author, block.index, block.prev, block.ts, block.addrs))
        digest.update(block.sig.toByteArray(Charsets.US_ASCII))
        return Hex.encode(digest.digest())
    }

    public fun checkShape(block: LedgerBlock) {
        checkId(block.author)
        if (block.index < 0 || block.ts < 0 || !hash.matches(block.prev) || !signature.matches(block.sig)) throw fail("field")
        if (block.addrs.isEmpty() || block.addrs.size > PeerEnvelope.MAX_ADDRS) throw fail("limit")
        if (!block.addrs.all(PeerAddress::check) || block.addrs.toSet().size != block.addrs.size) throw fail("field")
    }

    public fun verify(block: LedgerBlock) {
        checkShape(block)
        val verified = try {
            val signer = Ed25519Signer()
            signer.init(false, Ed25519PublicKeyParameters(Hex.decode(block.author), 0))
            val message = signedBytes(block.author, block.index, block.prev, block.ts, block.addrs)
            signer.update(message, 0, message.size)
            signer.verifySignature(Hex.decode(block.sig))
        } catch (_: RuntimeException) {
            false
        }
        if (!verified) throw fail("signature")
    }

    private fun text(element: JsonElement?): String =
        (element as? JsonPrimitive)?.takeIf { it.isString }?.content ?: throw fail("field")

    private fun integer(element: JsonElement?): Long =
        (element as? JsonPrimitive)?.takeIf { !it.isString }?.longOrNull ?: throw fail("field")

    public fun parseBlock(element: JsonElement?): LedgerBlock {
        val obj = element as? JsonObject ?: throw fail("field")
        if (obj.keys != blockFields) throw fail("field")
        val array = obj["addrs"] as? JsonArray ?: throw fail("field")
        val block = LedgerBlock(
            author = text(obj["author"]),
            index = integer(obj["index"]),
            prev = text(obj["prev"]),
            ts = integer(obj["ts"]),
            addrs = array.map { text(it) },
            sig = text(obj["sig"]),
        )
        checkShape(block)
        return block
    }

    public fun blockJson(block: LedgerBlock): JsonObject = buildJsonObject {
        put("author", block.author)
        put("index", block.index)
        put("prev", block.prev)
        put("ts", block.ts)
        put("addrs", JsonArray(block.addrs.map { JsonPrimitive(it) }))
        put("sig", block.sig)
    }

    public fun parseHead(element: JsonElement?): LedgerHead {
        val obj = element as? JsonObject ?: throw fail("field")
        if (obj.keys != headFields) throw fail("field")
        val head = LedgerHead(text(obj["author"]), integer(obj["index"]), text(obj["hash"]))
        checkId(head.author)
        if (head.index < 0 || !hash.matches(head.hash)) throw fail("field")
        return head
    }

    public fun headJson(head: LedgerHead): JsonObject = buildJsonObject {
        put("author", head.author)
        put("index", head.index)
        put("hash", head.hash)
    }
}
