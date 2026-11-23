package com.nuxiva.logic.peer

public class LocateTracker(
    serverId: String,
    private val clock: () -> Long = { System.currentTimeMillis() },
) {
    private val trusted = setOf(serverId)
    private var lastSeq = -1L

    @Synchronized
    public fun accept(raw: ByteArray): List<String>? {
        if (raw.size > PeerEnvelope.MAX_DATAGRAM) return null
        val text = try {
            Charsets.UTF_8.newDecoder().decode(java.nio.ByteBuffer.wrap(raw)).toString()
        } catch (_: java.nio.charset.CharacterCodingException) {
            return null
        }
        val locate = try {
            PeerEnvelope.verifyLocate(text, trusted)
        } catch (_: PeerException) {
            return null
        }
        if (kotlin.math.abs(clock() - locate.ts) > SKEW_MILLIS || locate.seq <= lastSeq) return null
        lastSeq = locate.seq
        return locate.addrs
    }

    public companion object {
        public const val SKEW_MILLIS: Long = 60_000L
    }
}
