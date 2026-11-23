package com.nuxiva.edge.node

import android.util.Log
import com.nuxiva.logic.peer.Ledger
import com.nuxiva.logic.peer.LedgerCodec
import com.nuxiva.logic.peer.LedgerException
import com.nuxiva.logic.peer.LedgerRules
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.put
import java.io.File
import java.io.IOException
import java.nio.file.Files
import java.nio.file.StandardCopyOption
import java.security.SecureRandom

class LedgerWatch(
    private val profile: NodeProfile,
    private val http: NodeHttp,
    private val file: File,
    private val isOnline: () -> Boolean,
    private val moveTo: (String) -> Unit,
    private val reachable: (String) -> Boolean = PeerWatch.PinnedProbe(profile.caPem)::check,
    private val clock: () -> Long = System::currentTimeMillis,
) {
    private val random = SecureRandom()
    private val ledger: Ledger = open()
    private var attempt = 0

    suspend fun run() {
        if (profile.peerId.isEmpty()) return
        while (currentCoroutineContext().isActive) {
            delay(withContext(Dispatchers.IO) { step() })
        }
    }

    internal fun step(): Long {
        if (isOnline()) {
            attempt = 0
            try {
                sync()
            } catch (error: CancellationException) {
                throw error
            } catch (error: NodeFailure) {
                Log.d(TAG, "Address ledger not synced: ${error.code}")
            } catch (error: LedgerException) {
                Log.w(TAG, "Address ledger reply refused: ${error.code}")
            } catch (error: IOException) {
                Log.w(TAG, "Address ledger not saved", error)
            }
            return SYNC_MILLIS
        }
        if (recover()) {
            attempt = 0
            return RETRY_MILLIS
        }
        val wait = LedgerRules.reconnectDelayMillis(attempt, random.nextLong())
        attempt = minOf(attempt + 1, MAX_ATTEMPT)
        return wait
    }

    private fun sync() {
        val request = LedgerCodec.encode(ledger.digestRequest())
        val reply = http.post("/api/nodes/peer/sync", buildJsonObject { put("wire", request) }, SYNC_TIMEOUT_SECONDS)
        val raw = reply["wire"]?.jsonPrimitive?.takeIf { it.isString }?.content ?: return
        val report = ledger.absorb(LedgerCodec.decode(raw), clock())
        if (report.applied > 0) persist()
    }

    private fun recover(): Boolean {
        val current = profile.server.removePrefix("https://")
        for (addr in ledger.candidates(profile.peerId).take(MAX_TRIES)) {
            if (addr == current || addr == "$current:443") continue
            if (!reachable(PeerWatch.serverUrl(addr))) {
                ledger.reportFailure(profile.peerId, addr)
                continue
            }
            if (isOnline()) return false
            Log.i(TAG, "Server found again from the address ledger")
            ledger.reportSuccess(profile.peerId, addr)
            moveTo(PeerWatch.serverUrl(addr))
            return true
        }
        return false
    }

    private fun persist() {
        val folder = file.parentFile ?: return
        folder.mkdirs()
        val temp = File(folder, file.name + ".tmp")
        temp.writeBytes(LedgerCodec.dump(ledger))
        Files.move(temp.toPath(), file.toPath(), StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING)
    }

    private fun open(): Ledger {
        val trusted = listOf(profile.peerId).filter { it.isNotEmpty() }
        return try {
            if (file.isFile && file.length() <= LedgerRules.MAX_FILE) {
                LedgerCodec.restore(trusted, file.readBytes(), clock())
            } else {
                Ledger(trusted)
            }
        } catch (error: LedgerException) {
            Log.w(TAG, "Address ledger unreadable, starting empty: ${error.code}")
            Ledger()
        } catch (error: IOException) {
            Log.w(TAG, "Address ledger unreadable, starting empty", error)
            Ledger()
        }
    }

    companion object {
        private const val TAG = "NuxivaLedger"
        private const val SYNC_MILLIS = 60_000L
        private const val RETRY_MILLIS = 1_000L
        private const val SYNC_TIMEOUT_SECONDS = 10L
        private const val MAX_TRIES = 3
        private const val MAX_ATTEMPT = 16

        fun fileFor(folder: File, nodeId: String): File {
            val safe = nodeId.filter { it.isLetterOrDigit() || it == '-' || it == '_' }.take(64).ifEmpty { "node" }
            return File(folder, "$safe.chain")
        }
    }
}
