package com.nuxiva.logic.peer

public class SourceThrottle(
    private val perWindow: Int = 8,
    private val windowMillis: Long = 1_000L,
    private val clock: () -> Long = { System.nanoTime() / 1_000_000L },
) {
    private val seen = HashMap<String, Pair<Long, Int>>()

    @Synchronized
    public fun allow(source: String): Boolean {
        val now = clock()
        if (seen.size >= MAX_SOURCES && source !in seen) {
            seen.entries.removeIf { now - it.value.first >= windowMillis }
            if (seen.size >= MAX_SOURCES) return false
        }
        val current = seen[source]
        val fresh = current == null || now - current.first >= windowMillis
        val start = if (fresh) now else current!!.first
        val count = (if (fresh) 0 else current!!.second) + 1
        seen[source] = start to count
        return count <= perWindow
    }

    public companion object {
        public const val MAX_SOURCES: Int = 1024
    }
}
