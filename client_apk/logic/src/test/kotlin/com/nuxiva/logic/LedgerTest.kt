package com.nuxiva.logic

import com.nuxiva.logic.peer.Ledger
import com.nuxiva.logic.peer.LedgerBlock
import com.nuxiva.logic.peer.LedgerCodec
import com.nuxiva.logic.peer.LedgerException
import com.nuxiva.logic.peer.LedgerRules
import com.nuxiva.logic.peer.LedgerWire
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import java.io.File
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertTrue

class LedgerTest {
    private val relative = "native/crates/peer-ledger/tests/fixtures/ledger.json"

    private fun fixture(): JsonObject {
        var dir: File? = File("").absoluteFile
        while (dir != null && !File(dir, relative).isFile) dir = dir.parentFile
        return Json.parseToJsonElement(requireNotNull(dir) { "$relative not found" }.resolve(relative).readText()).jsonObject
    }

    private val data = fixture()
    private val now = data.getValue("now").jsonPrimitive.content.toLong()
    private val trusted = data.getValue("trusted").jsonArray.map { it.jsonPrimitive.content }
    private val steps = data.getValue("steps").jsonArray.map { it.jsonObject }

    private fun verdict(ledger: Ledger, step: JsonObject): String = try {
        if (ledger.accept(LedgerRules.parseBlock(step.getValue("block")), now)) "new" else "known"
    } catch (error: LedgerException) {
        error.code
    }

    private fun filled(count: Int = 6): Ledger {
        val ledger = Ledger(trusted)
        steps.take(count).forEach { verdict(ledger, it) }
        return ledger
    }

    @Test
    fun everyStepMatchesTheRustVerdictAndHash() {
        val ledger = Ledger(trusted)
        steps.forEach { step ->
            val name = step.getValue("name").jsonPrimitive.content
            assertEquals(step.getValue("expect").jsonPrimitive.content, verdict(ledger, step), name)
            val parsed = runCatching { LedgerRules.parseBlock(step.getValue("block")) }.getOrNull()
            if (parsed != null) assertEquals(step.getValue("hash").jsonPrimitive.content, LedgerRules.hash(parsed), name)
        }
        val heads = data.getValue("heads").jsonArray.map { it.jsonObject }
        assertEquals(
            heads.map { it.getValue("hash").jsonPrimitive.content },
            ledger.digest().map { it.hash },
        )
        assertEquals(data.getValue("candidates").jsonArray.map { it.jsonPrimitive.content }, ledger.candidates(trusted.first()))
    }

    @Test
    fun everyWireCaseMatchesTheRustVerdict() {
        data.getValue("wires").jsonArray.map { it.jsonObject }.forEach { case ->
            val name = case.getValue("name").jsonPrimitive.content
            val got = try {
                LedgerCodec.decode(case.getValue("raw").jsonPrimitive.content)
                "ok"
            } catch (error: LedgerException) {
                error.code
            }
            assertEquals(case.getValue("expect").jsonPrimitive.content, got, name)
        }
    }

    @Test
    fun deltaRebuildsTheChainOnAnEmptyLedger() {
        val full = filled()
        val raw = data.getValue("wires").jsonArray.map { it.jsonObject }
            .first { it.getValue("name").jsonPrimitive.content == "delta" }.getValue("raw").jsonPrimitive.content
        val wire = LedgerCodec.decode(raw)
        assertTrue(wire is LedgerWire.Delta)
        val empty = Ledger(trusted)
        val report = empty.absorb(wire, now)
        assertEquals(3, report.applied)
        assertEquals(full.digest(), empty.digest())
        assertEquals(Json.parseToJsonElement(raw), Json.parseToJsonElement(LedgerCodec.encode(wire)))
    }

    @Test
    fun snapshotRoundTripsAndRefusesTampering() {
        val full = filled()
        val bytes = LedgerCodec.dump(full)
        assertEquals(full.digest(), LedgerCodec.restore(trusted, bytes, now).digest())
        val forged = String(bytes, Charsets.UTF_8).replace("192.168.1.12", "192.168.1.99").toByteArray(Charsets.UTF_8)
        assertEquals("ledger.error.corrupt", assertFailsWith<LedgerException> { LedgerCodec.restore(trusted, forged, now) }.code)
    }

    @Test
    fun answerAndFailureRankingBehaveLikeRust() {
        val full = filled()
        val have = full.answer(LedgerWire.Want(trusted.first()))
        assertTrue(have is LedgerWire.Have)
        val head = (have as LedgerWire.Have).block
        assertEquals(listOf("192.168.1.12:8443", "nodo-12.local:8443"), head.addrs)
        full.reportFailure(trusted.first(), "192.168.1.12:8443")
        assertEquals("nodo-12.local:8443", full.candidates(trusted.first()).first())
        full.reportSuccess(trusted.first(), "192.168.1.12:8443")
        assertEquals("192.168.1.12:8443", full.candidates(trusted.first()).first())
    }

    @Test
    fun blocksFromStrangersAndShapeViolationsNeverChangeTheLedger() {
        val ledger = Ledger(trusted)
        val block: LedgerBlock = LedgerRules.parseBlock(steps.first().getValue("block"))
        assertEquals("ledger.error.untrusted", assertFailsWith<LedgerException> { Ledger().accept(block, now) }.code)
        assertEquals("ledger.error.field", assertFailsWith<LedgerException> { ledger.accept(block.copy(ts = -1), now) }.code)
    }

    @Test
    fun reconnectDelayGrowsIsCappedAndJittered() {
        assertEquals(1_000L, LedgerRules.reconnectDelayMillis(0, 0))
        assertEquals(4_000L, LedgerRules.reconnectDelayMillis(2, 0))
        assertEquals(1_000L + 7L, LedgerRules.reconnectDelayMillis(0, 7))
        assertTrue(LedgerRules.reconnectDelayMillis(99, Long.MAX_VALUE) in 60_000L..75_000L)
        assertTrue(LedgerRules.reconnectDelayMillis(-3, -5) in 1_000L..1_250L)
    }
}
