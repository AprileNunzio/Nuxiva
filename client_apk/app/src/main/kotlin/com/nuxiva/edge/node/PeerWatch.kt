package com.nuxiva.edge.node

import android.util.Log
import com.nuxiva.logic.peer.LocateTracker
import com.nuxiva.logic.peer.PeerEnvelope
import com.nuxiva.logic.peer.SourceThrottle
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.isActive
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.IOException
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetSocketAddress
import java.net.SocketTimeoutException
import java.util.concurrent.TimeUnit

class PeerWatch(
    private val profile: NodeProfile,
    private val isOnline: () -> Boolean,
    private val moveTo: (String) -> Unit,
    private val reachable: (String) -> Boolean = PinnedProbe(profile.caPem)::check,
    private val port: Int = PEER_PORT,
) {
    private val tracker = LocateTracker(profile.peerId)
    private val throttle = SourceThrottle()

    suspend fun run() {
        if (profile.peerId.isEmpty()) return
        withContext(Dispatchers.IO) {
            DatagramSocket(null).use { socket ->
                socket.reuseAddress = true
                socket.bind(InetSocketAddress(port))
                socket.soTimeout = RECEIVE_TIMEOUT_MILLIS
                val buffer = ByteArray(PeerEnvelope.MAX_DATAGRAM + 1)
                while (currentCoroutineContext().isActive) {
                    val packet = DatagramPacket(buffer, buffer.size)
                    try {
                        socket.receive(packet)
                    } catch (_: SocketTimeoutException) {
                        continue
                    }
                    val source = packet.address?.hostAddress ?: continue
                    if (throttle.allow(source)) handle(buffer.copyOf(packet.length))
                }
            }
        }
    }

    internal fun handle(raw: ByteArray): Boolean {
        val addrs = tracker.accept(raw) ?: return false
        if (isOnline()) return false
        val current = profile.server.removePrefix("https://")
        for (addr in addrs.take(MAX_TRIES)) {
            if (addr == current || addr == "$current:443") continue
            val url = serverUrl(addr)
            if (!reachable(url) || isOnline()) continue
            Log.i(TAG, "Server found at a new address")
            moveTo(url)
            return true
        }
        return false
    }

    class PinnedProbe(caPem: String) {
        private val client: OkHttpClient by lazy {
            TlsClients.pinned(caPem).newBuilder()
                .connectTimeout(PROBE_SECONDS, TimeUnit.SECONDS)
                .readTimeout(PROBE_SECONDS, TimeUnit.SECONDS)
                .build()
        }

        fun check(url: String): Boolean = try {
            client.newCall(Request.Builder().url("$url$CA_PATH").get().build()).execute().use { it.code == 200 }
        } catch (_: IOException) {
            false
        }
    }

    companion object {
        const val PEER_PORT = 50507
        private const val TAG = "NuxivaPeer"
        private const val CA_PATH = "/nuxiva-ca.crt"
        private const val RECEIVE_TIMEOUT_MILLIS = 1000
        private const val MAX_TRIES = 3
        private const val PROBE_SECONDS = 4L

        fun serverUrl(addr: String): String {
            val cut = addr.lastIndexOf(':')
            val host = addr.substring(0, cut)
            return if (addr.substring(cut + 1) == "443") "https://$host" else "https://$addr"
        }
    }
}
