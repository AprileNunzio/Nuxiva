package com.nuxiva.logic

import com.nuxiva.logic.crypto.DeviceKey
import com.nuxiva.logic.crypto.Hex
import com.nuxiva.logic.enroll.EnrollmentException
import com.nuxiva.logic.enroll.EnrollmentParser
import com.nuxiva.logic.peer.LocateTracker
import com.nuxiva.logic.peer.PeerAddress
import com.nuxiva.logic.peer.PeerEnvelope
import com.nuxiva.logic.peer.PeerException
import com.nuxiva.logic.peer.SourceThrottle
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import java.io.File
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

class PeerTest {
    private val relative = "native/crates/peer-core/tests/fixtures/locate.json"
    private val key = DeviceKey.fromSeed(ByteArray(32) { it.toByte() })
    private val other = DeviceKey.fromSeed(ByteArray(32) { (it + 1).toByte() })
    private val now = 1_700_000_000_000L

    private fun fixture(): JsonObject {
        var dir: File? = File("").absoluteFile
        while (dir != null && !File(dir, relative).isFile) dir = dir.parentFile
        return Json.parseToJsonElement(requireNotNull(dir) { "$relative not found" }.resolve(relative).readText()).jsonObject
    }

    private fun record(signer: DeviceKey = key, seq: Long = 1, ts: Long = now, addrs: String = "\"192.168.1.20:8443\""): ByteArray {
        val sender = signer.publicHex()
        val payload = "{\"type\":\"locate\",\"addrs\":[$addrs]}"
        val sig = Hex.encode(signer.sign(PeerEnvelope.signedBytes(sender, seq, ts, payload)))
        val escaped = payload.replace("\"", "\\\"")
        return "{\"from\":\"$sender\",\"seq\":$seq,\"ts\":$ts,\"ttl\":6,\"payload\":\"$escaped\",\"sig\":\"$sig\"}".toByteArray()
    }

    @Test
    fun everySharedCaseMatchesTheRustVerdict() {
        val data = fixture()
        val trusted = data.getValue("trusted").jsonArray.map { it.jsonPrimitive.content }.toSet()
        val cases = data.getValue("cases") as JsonArray
        assertTrue(cases.isNotEmpty())
        cases.forEach { element ->
            val case = element.jsonObject
            val name = case.getValue("name").jsonPrimitive.content
            val expected = case.getValue("expect").jsonPrimitive.content
            val got = try {
                PeerEnvelope.verifyLocate(case.getValue("envelope").toString(), trusted)
                "ok"
            } catch (error: PeerException) {
                error.code
            }
            assertEquals(expected, got, name)
        }
    }

    @Test
    fun freshRecordIsAcceptedOncePerSequence() {
        val tracker = LocateTracker(key.publicHex()) { now }
        assertEquals(listOf("192.168.1.20:8443"), tracker.accept(record(seq = 5)))
        assertNull(tracker.accept(record(seq = 5)))
        assertNull(tracker.accept(record(seq = 4)))
        assertNotNull(tracker.accept(record(seq = 6)))
    }

    @Test
    fun staleFutureForeignAndMalformedRecordsAreDropped() {
        val tracker = LocateTracker(key.publicHex()) { now }
        listOf(
            record(ts = now - 61_000), record(ts = now + 61_000), record(signer = other),
            "{".toByteArray(), byteArrayOf(0xff.toByte(), 0xfe.toByte()), ByteArray(1300) { 'x'.code.toByte() },
            record(addrs = "\"0.0.0.0:80\""),
        ).forEachIndexed { index, raw -> assertNull(tracker.accept(raw), "case $index") }
    }

    @Test
    fun rejectedRecordDoesNotAdvanceTheSequence() {
        val tracker = LocateTracker(key.publicHex()) { now }
        assertNull(tracker.accept(record(signer = other, seq = 99)))
        assertNotNull(tracker.accept(record(seq = 1)))
    }

    @Test
    fun addressRulesMatchTheServer() {
        listOf("[2001:db8::1]:7000", "nodo-1.local:7000", "10.1.2.3:443", "[::1]:80", "192.168.1.20:7000").forEach {
            assertTrue(PeerAddress.check(it), it)
        }
        listOf(
            "0.0.0.0:80", "224.0.0.1:80", "10.0.0.1:0", "http://x:80", "-a.b:80", "host", "255.255.255.255:9", "[::]:80",
            "2001:db8::1:80", "[10.0.0.1]:80", "10.0.0.1:99999", ":80", "[ff02::1]:80", "10.0.0.1:", "a b.local:80",
        ).forEach { assertFalse(PeerAddress.check(it), it) }
    }

    @Test
    fun oversizeAndTypeConfusionAreRefused() {
        val trusted = setOf(key.publicHex())
        val good = String(record())
        assertEquals("peer.error.untrusted", assertFailsWith<PeerException> { PeerEnvelope.verifyLocate(good, setOf(other.publicHex())) }.code)
        assertEquals("peer.error.payload", assertFailsWith<PeerException> { PeerEnvelope.verifyLocate(good.replace("\"seq\":1", "\"seq\":true"), trusted) }.code)
        assertEquals("peer.error.payload", assertFailsWith<PeerException> { PeerEnvelope.verifyLocate(good.dropLast(1) + ",\"extra\":1}", trusted) }.code)
        assertEquals("peer.error.limit", assertFailsWith<PeerException> { PeerEnvelope.verifyLocate(good.replace("\"ttl\":6", "\"ttl\":99"), trusted) }.code)
        assertEquals("peer.error.signature", assertFailsWith<PeerException> { PeerEnvelope.verifyLocate(good.replace("\"sig\":\"", "\"sig\":\"00"), trusted) }.code)
    }

    @Test
    fun sourceIsRateLimitedAndTheTableIsBounded() {
        var clock = 0L
        val throttle = SourceThrottle(3, 1_000L) { clock }
        assertEquals(listOf(true, true, true, false, false), (1..5).map { throttle.allow("a") })
        assertTrue(throttle.allow("b"))
        clock = 2_000L
        assertTrue(throttle.allow("a"))
        val bounded = SourceThrottle(1, 1_000_000L) { 0L }
        (0 until SourceThrottle.MAX_SOURCES).forEach { bounded.allow("$it") }
        assertFalse(bounded.allow("new"))
    }

    @Test
    fun enrollmentCarriesTheServerIdWhenPresent() {
        val token = "T".repeat(43)
        val pin = "ab".repeat(32)
        fun json(extra: String) = """{"server":"https://192.168.1.10:8443","token":"$token","pin":"$pin","expires":2000$extra}"""
        assertEquals("", EnrollmentParser.parse(json(""), 1_000L).peer)
        assertEquals("cd".repeat(32), EnrollmentParser.parse(json(",\"peer\":\"${"cd".repeat(32)}\""), 1_000L).peer)
        listOf(",\"peer\":\"zz\"", ",\"peer\":5", ",\"peer\":null", ",\"peer\":\"${"CD".repeat(32)}\"").forEach { extra ->
            assertEquals("enroll_file_invalid", assertFailsWith<EnrollmentException>(extra) { EnrollmentParser.parse(json(extra), 1_000L) }.code)
        }
    }
}
