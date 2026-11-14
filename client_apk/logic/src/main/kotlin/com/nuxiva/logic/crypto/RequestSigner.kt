package com.nuxiva.logic.crypto

import java.security.MessageDigest
import java.security.SecureRandom

public class RequestSigner(
    private val nodeId: String,
    private val key: DeviceKey,
    private val clock: () -> Long = { System.currentTimeMillis() / 1000L },
    private val random: SecureRandom = SecureRandom(),
) {
    public fun headers(method: String, path: String, body: ByteArray): Map<String, String> {
        val nonce = ByteArray(NONCE_BYTES).also(random::nextBytes).let(Hex::encode)
        return headersAt(method, path, body, clock(), nonce)
    }

    public fun headersAt(method: String, path: String, body: ByteArray, timestamp: Long, nonce: String): Map<String, String> {
        val signature = key.sign(canonical(nodeId, method, path, timestamp, nonce, body))
        return mapOf(
            NODE_HEADER to nodeId,
            TIMESTAMP_HEADER to timestamp.toString(),
            NONCE_HEADER to nonce,
            SIGNATURE_HEADER to Hex.encode(signature),
        )
    }

    public companion object {
        public const val DOMAIN: String = "nuxiva-node-v1"
        public const val NODE_HEADER: String = "X-Nuxiva-Node"
        public const val TIMESTAMP_HEADER: String = "X-Nuxiva-Ts"
        public const val NONCE_HEADER: String = "X-Nuxiva-Nonce"
        public const val SIGNATURE_HEADER: String = "X-Nuxiva-Sig"
        private const val NONCE_BYTES = 16

        public fun canonical(node: String, method: String, path: String, timestamp: Long, nonce: String, body: ByteArray): ByteArray {
            val digest = Hex.encode(MessageDigest.getInstance("SHA-256").digest(body))
            return listOf(DOMAIN, node, method, path, timestamp.toString(), nonce, digest).joinToString("\n").toByteArray(Charsets.UTF_8)
        }
    }
}
