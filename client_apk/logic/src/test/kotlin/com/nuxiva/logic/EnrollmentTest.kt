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
            json(server = "https://host/path"), json(server = "https://host?x=1"), json(extra = ",\"extra\":1"),
            json().replace(token, "short"), json().replace(pin, "AB".repeat(32)),
            "nuxiva://enroll", "nuxiva://other?d=e30", "nuxiva://enroll?d=@@@",
        ).forEach { raw ->
            assertEquals("enroll_file_invalid", assertFailsWith<EnrollmentException>(raw) { EnrollmentParser.parse(raw, 1_000L) }.code)
        }
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
}
