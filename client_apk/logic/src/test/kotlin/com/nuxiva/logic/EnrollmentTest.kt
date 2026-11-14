package com.nuxiva.logic

import com.nuxiva.logic.enroll.EnrollmentException
import com.nuxiva.logic.enroll.EnrollmentParser
import java.util.Base64
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith

class EnrollmentTest {
    private val token = "T".repeat(43)
    private val pin = "ab".repeat(32)

    private fun json(server: String = "https://192.168.1.10:8443", expires: Long = 2_000L, extra: String = "") =
        """{"server":"$server","token":"$token","pin":"$pin","expires":$expires$extra}"""

    @Test
    fun acceptsPlainJsonAndDeepLink() {
        val plain = EnrollmentParser.parse(json(), 1_000L)
        assertEquals("https://192.168.1.10:8443", plain.server)
        val encoded = Base64.getUrlEncoder().withoutPadding().encodeToString(json().toByteArray())
        assertEquals(plain, EnrollmentParser.parse("nuxiva://enroll?d=$encoded", 1_000L))
    }

    @Test
    fun rejectsExpiredAndMalformedPayloads() {
        assertEquals("enroll_file_expired", assertFailsWith<EnrollmentException> { EnrollmentParser.parse(json(expires = 10L), 1_000L) }.code)
        listOf(
            "", "{", "[]", json(server = "http://192.168.1.10"), json(server = "https://user@host"),
            json(server = "https://host/path"), json(server = "https://host?x=1"), json(server = "https://host:99999"),
            json().replace(token, "short"), json().replace(pin, "AB".repeat(32)),
            "nuxiva://enroll", "nuxiva://other?d=e30", "nuxiva://enroll?d=@@@",
        ).forEach { raw ->
            assertEquals("enroll_file_invalid", assertFailsWith<EnrollmentException>(raw) { EnrollmentParser.parse(raw, 1_000L) }.code)
        }
    }

    @Test
    fun toleratesWhatPeopleActuallyPaste() {
        val expected = EnrollmentParser.parse(json(), 1_000L)
        val encoded = Base64.getUrlEncoder().withoutPadding().encodeToString(json().toByteArray())
        val padded = Base64.getUrlEncoder().encodeToString(json().toByteArray())
        listOf(
            "  nuxiva://enroll?d=$encoded\n", "NUXIVA://ENROLL?d=$encoded", "nuxiva://enroll?d=$padded", "nuxiva://enroll?d=${encoded.take(20)}\n${encoded.drop(20)}",
            "nuxiva://enroll?d=${padded.replace("=", "%3D")}", encoded, padded, "\"nuxiva://enroll?d=$encoded\"", json(extra = ",\"v\":1"),
            json().replace("2000", "2000.0"),
        ).forEach { raw -> assertEquals(expected, EnrollmentParser.parse(raw, 1_000L), raw) }
    }

    @Test
    fun acceptsHostsThatJavaUriRejects() {
        assertEquals("https://nuxiva_pc.lan:8443", EnrollmentParser.parse(json(server = "https://nuxiva_pc.lan:8443"), 1_000L).server)
        assertEquals("https://[fe80::1]:8443", EnrollmentParser.parse(json(server = "https://[fe80::1]:8443"), 1_000L).server)
    }

    @Test
    fun rejectsOversizedPayloads() {
        val big = json(extra = ",\"pad\":\"" + "x".repeat(5000) + "\"")
        assertFailsWith<EnrollmentException> { EnrollmentParser.parse(big, 1_000L) }
    }

    @Test
    fun defaultPortIsDropped() {
        assertEquals("https://nuxiva.local", EnrollmentParser.parse(json(server = "https://nuxiva.local:443/"), 1_000L).server)
    }
}

class NodeIdTest {
    @kotlin.test.Test
    fun generatedIdsFitTheServerPattern() {
        listOf("Pixel 8 Pro", "ÄÖÜ", "", "A".repeat(200), "---").forEach {
            val id = com.nuxiva.logic.enroll.NodeIds.generate(it)
            kotlin.test.assertTrue(com.nuxiva.logic.enroll.NodeIds.pattern.matches(id), id)
        }
    }


    @Test
    fun normalizesManualCodeAndServer() {
        assertEquals("482915", EnrollmentParser.normalizeCode("482 915"))
        assertEquals("enroll_code_invalid", assertFailsWith<EnrollmentException> { EnrollmentParser.normalizeCode("12345") }.code)
        assertEquals("https://192.168.1.10:8443", EnrollmentParser.normalizeServerInput("192.168.1.10:8443/"))
        assertEquals("https://nuxiva.local", EnrollmentParser.normalizeServerInput("https://nuxiva.local:443"))
        assertFailsWith<EnrollmentException> { EnrollmentParser.normalizeServerInput("http://192.168.1.10") }
        assertFailsWith<EnrollmentException> { EnrollmentParser.normalizeServerInput("a b") }
    }
}
