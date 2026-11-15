package com.nuxiva.logic

import com.nuxiva.logic.update.UpdatePolicy
import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

class UpdateTest {
    private val hash = "a".repeat(64)
    private fun offer(url: String, version: String = "5.8.4", sha: String = hash) =
        Json.parseToJsonElement("""{"version":"$version","url":"$url","sha256":"$sha","size":1234}""")

    @Test
    fun acceptsOfficialRelease() {
        val parsed = UpdatePolicy.parse(offer("https://github.com/AprileNunzio/Nuxiva/releases/download/v5.8.4/Nuxiva.apk"))
        assertNotNull(parsed)
        assertEquals("5.8.4", parsed!!.version)
        assertEquals(1234L, parsed.sizeBytes)
    }

    @Test
    fun rejectsForeignHostsAndPaths() {
        assertNull(UpdatePolicy.parse(offer("https://evil.example/releases/download/v5.8.4/Nuxiva.apk")))
        assertNull(UpdatePolicy.parse(offer("http://github.com/AprileNunzio/Nuxiva/releases/download/v5.8.4/Nuxiva.apk")))
        assertNull(UpdatePolicy.parse(offer("https://github.com/AprileNunzio/Nuxiva/releases/download/v5.8.4/../x/Nuxiva.apk")))
        assertNull(UpdatePolicy.parse(offer("https://github.com/AprileNunzio/Nuxiva/releases/download/v5.8.4/Other.apk")))
        assertNull(UpdatePolicy.parse(offer("https://github.com/AprileNunzio/Nuxiva/releases/download/v5.8.4/Nuxiva.apk?x=1")))
    }

    @Test
    fun rejectsBadHashOrVersion() {
        val url = "https://github.com/AprileNunzio/Nuxiva/releases/download/v5.8.4/Nuxiva.apk"
        assertNull(UpdatePolicy.parse(offer(url, sha = "zz")))
        assertNull(UpdatePolicy.parse(offer(url, version = "5.8.x")))
        assertNull(UpdatePolicy.parse(null))
    }

    @Test
    fun comparesVersions() {
        assertTrue(UpdatePolicy.isNewer("5.8.4", "5.8.3"))
        assertTrue(UpdatePolicy.isNewer("v5.10.0", "5.9.9"))
        assertFalse(UpdatePolicy.isNewer("5.8.3", "5.8.3"))
        assertFalse(UpdatePolicy.isNewer("5.8.2", "5.8.3"))
        assertFalse(UpdatePolicy.isNewer("garbage", "5.8.3"))
    }

    @Test
    fun cleansErrorCodes() {
        assertEquals("hash_mismatch", UpdatePolicy.safeCode("Hash Mismatch".replace(' ', '_')))
        assertEquals(48, UpdatePolicy.safeCode("x".repeat(100)).length)
        assertEquals("error", UpdatePolicy.safeCode(""))
    }
}
