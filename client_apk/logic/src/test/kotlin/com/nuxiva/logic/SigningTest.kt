package com.nuxiva.logic

import com.nuxiva.logic.crypto.DeviceKey
import com.nuxiva.logic.crypto.Hex
import com.nuxiva.logic.crypto.RequestSigner
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertNotEquals

class SigningTest {
    private val seed = ByteArray(32) { it.toByte() }

    @Test
    fun publicKeyAndSignatureMatchTheServerImplementation() {
        val key = DeviceKey.fromSeed(seed)
        assertEquals("03a107bff3ce10be1d70dd18e74bc09967e4d6309ba50d5f1ddc8664125531b8", key.publicHex())
        val signer = RequestSigner("android-test-ab12cd", key)
        val headers = signer.headersAt("POST", "/api/nodes/heartbeat?x=1", "{\"a\":1}".toByteArray(), 1760000000L, "00112233445566778899aabbccddeeff")
        assertEquals(
            "6a58ada4483ff467842b6f3eac35bd7ac989968554321adc4dfe7d9d89ed25030f919a422aa1bd934098829e77a3031d0ec8d70355646c04b7e10773f975170b",
            headers[RequestSigner.SIGNATURE_HEADER],
        )
        assertEquals("android-test-ab12cd", headers[RequestSigner.NODE_HEADER])
        assertEquals("1760000000", headers[RequestSigner.TIMESTAMP_HEADER])
    }

    @Test
    fun everyRequestUsesAFreshNonce() {
        val signer = RequestSigner("android-test-ab12cd", DeviceKey.generate())
        val first = signer.headers("POST", "/api/nodes/heartbeat", ByteArray(0))
        val second = signer.headers("POST", "/api/nodes/heartbeat", ByteArray(0))
        assertNotEquals(first[RequestSigner.NONCE_HEADER], second[RequestSigner.NONCE_HEADER])
        assertEquals(32, first.getValue(RequestSigner.NONCE_HEADER).length)
    }

    @Test
    fun seedLengthIsEnforcedAndHexRoundTrips() {
        assertFailsWith<IllegalArgumentException> { DeviceKey.fromSeed(ByteArray(31)) }
        assertEquals("00ff10", Hex.encode(Hex.decode("00ff10")))
        assertFailsWith<IllegalArgumentException> { Hex.decode("zz") }
    }

    @Test
    fun wipeClearsTheInternalSeedCopyOnly() {
        val key = DeviceKey.fromSeed(seed)
        val copy = key.seedBytes()
        key.wipe()
        assertEquals(seed.toList(), copy.toList())
        assertEquals(ByteArray(32).toList(), key.seedBytes().toList())
    }
}
