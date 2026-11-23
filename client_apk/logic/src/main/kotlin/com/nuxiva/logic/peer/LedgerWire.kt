package com.nuxiva.logic.peer

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.int
import kotlinx.serialization.json.put

public sealed interface LedgerWire {
    public data class Want(val id: String) : LedgerWire
    public data class Have(val block: LedgerBlock) : LedgerWire
    public data class Digest(val heads: List<LedgerHead>) : LedgerWire
    public data class Delta(val blocks: List<LedgerBlock>) : LedgerWire
}

public object LedgerCodec {
    private val json = Json { isLenient = false }

    private fun parse(raw: String): JsonObject {
        if (raw.toByteArray(Charsets.UTF_8).size > LedgerRules.MAX_WIRE) throw LedgerRules.fail("limit")
        val parsed = try {
            json.parseToJsonElement(raw) as? JsonObject
        } catch (_: Exception) {
            null
        }
        return parsed ?: throw LedgerRules.fail("field")
    }

    public fun decode(raw: String): LedgerWire {
        val obj = parse(raw)
        val kind = (obj["t"] as? JsonPrimitive)?.takeIf { it.isString }?.content
        return when {
            kind == "want" && obj.keys == setOf("t", "id") -> {
                val id = (obj["id"] as? JsonPrimitive)?.takeIf { it.isString }?.content ?: throw LedgerRules.fail("field")
                LedgerRules.checkId(id)
                LedgerWire.Want(id)
            }
            kind == "have" && obj.keys == setOf("t", "block") -> LedgerWire.Have(LedgerRules.parseBlock(obj["block"]))
            kind == "digest" && obj.keys == setOf("t", "heads") -> {
                val heads = obj["heads"] as? JsonArray ?: throw LedgerRules.fail("field")
                if (heads.size > LedgerRules.MAX_AUTHORS) throw LedgerRules.fail("limit")
                LedgerWire.Digest(heads.map { LedgerRules.parseHead(it) })
            }
            kind == "delta" && obj.keys == setOf("t", "blocks") -> {
                val blocks = obj["blocks"] as? JsonArray ?: throw LedgerRules.fail("field")
                if (blocks.size > LedgerRules.MAX_SYNC) throw LedgerRules.fail("limit")
                LedgerWire.Delta(blocks.map { LedgerRules.parseBlock(it) })
            }
            else -> throw LedgerRules.fail("field")
        }
    }

    public fun encode(wire: LedgerWire): String {
        val obj = when (wire) {
            is LedgerWire.Want -> buildJsonObject {
                put("t", "want")
                put("id", wire.id)
            }
            is LedgerWire.Have -> buildJsonObject {
                put("t", "have")
                put("block", LedgerRules.blockJson(wire.block))
            }
            is LedgerWire.Digest -> buildJsonObject {
                put("t", "digest")
                put("heads", JsonArray(wire.heads.map { LedgerRules.headJson(it) }))
            }
            is LedgerWire.Delta -> buildJsonObject {
                put("t", "delta")
                put("blocks", JsonArray(wire.blocks.map { LedgerRules.blockJson(it) }))
            }
        }
        val text = obj.toString()
        if (text.toByteArray(Charsets.UTF_8).size > LedgerRules.MAX_WIRE) throw LedgerRules.fail("limit")
        return text
    }

    public fun dump(ledger: Ledger): ByteArray {
        val text = buildJsonObject {
            put("v", 1)
            put("blocks", JsonArray(ledger.snapshot().map { LedgerRules.blockJson(it) }))
        }.toString().toByteArray(Charsets.UTF_8)
        if (text.size > LedgerRules.MAX_FILE) throw LedgerRules.fail("limit")
        return text
    }

    public fun restore(trusted: Collection<String>, raw: ByteArray, now: Long): Ledger {
        if (raw.size > LedgerRules.MAX_FILE) throw LedgerRules.fail("limit")
        val parsed = try {
            json.parseToJsonElement(String(raw, Charsets.UTF_8)) as? JsonObject
        } catch (_: Exception) {
            null
        }
        val obj = parsed ?: throw LedgerRules.fail("corrupt")
        val version = (obj["v"] as? JsonPrimitive)?.takeIf { !it.isString }?.let { runCatching { it.int }.getOrNull() }
        val blocks = obj["blocks"] as? JsonArray
        if (obj.keys != setOf("v", "blocks") || version != 1 || blocks == null) throw LedgerRules.fail("corrupt")
        val ledger = Ledger(trusted)
        try {
            blocks.map { LedgerRules.parseBlock(it) }
                .sortedWith(compareBy({ it.author }, { it.index }))
                .forEach { ledger.accept(it, now) }
        } catch (_: LedgerException) {
            throw LedgerRules.fail("corrupt")
        }
        return ledger
    }
}
