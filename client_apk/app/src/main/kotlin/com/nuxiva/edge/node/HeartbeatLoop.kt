package com.nuxiva.edge.node

import android.util.Log
import com.nuxiva.edge.device.OrientationMonitor
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.drop
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.isActive
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonPrimitive

class HeartbeatLoop(
    private val profile: NodeProfile,
    private val http: NodeHttp,
    private val reports: ReportBuilder,
    private val orientation: OrientationMonitor,
    private val sharing: () -> Boolean,
    private val computeOffered: () -> Boolean,
    private val onState: (LinkState) -> Unit,
    private val onEvent: (RuntimeEvent) -> Unit,
) {
    suspend fun run() {
        var adapted = false
        var online = false
        while (currentCoroutineContext().isActive) {
            var interval = DEFAULT_INTERVAL
            try {
                if (!online) onState(LinkState.Connecting)
                val body = withContext(Dispatchers.IO) { reports.build(sharing(), computeOffered(), adapted) }
                adapted = false
                val reply = withContext(Dispatchers.IO) { http.post("/api/nodes/heartbeat", body, HEARTBEAT_TIMEOUT) }
                online = true
                onState(LinkState.Online(System.currentTimeMillis() / 1000L))
                interval = (reply["heartbeat"]?.jsonPrimitive?.intOrNull ?: DEFAULT_INTERVAL.toInt()).coerceIn(MIN_INTERVAL, MAX_INTERVAL).toLong()
                adapted = handle(reply)
            } catch (error: CancellationException) {
                throw error
            } catch (error: NodeFailure.Unauthorized) {
                onState(LinkState.Revoked)
                return
            } catch (error: NodeFailure.Pin) {
                onState(LinkState.SecurityAlert(error.code))
                return
            } catch (error: NodeFailure) {
                online = false
                Log.w(TAG, "Heartbeat failed for ${profile.nodeId}: ${error.code}")
                onState(LinkState.Offline(error.code))
            }
            withTimeoutOrNull(interval * 1000L) { orientation.current.drop(1).first() }
            delay(DEBOUNCE_MILLIS)
        }
    }

    private fun handle(reply: JsonObject): Boolean {
        var adapt = false
        (reply["commands"] as? JsonArray)?.forEach { element ->
            when (element.jsonPrimitive.contentOrNull) {
                "identify" -> onEvent(RuntimeEvent.Identify(profile.nodeId))
                "adapt" -> adapt = true
                else -> Log.i(TAG, "Command not supported on Android: ${element.jsonPrimitive.contentOrNull}")
            }
        }
        return adapt
    }

    private companion object {
        const val TAG = "NuxivaHeartbeat"
        const val DEFAULT_INTERVAL = 30L
        const val MIN_INTERVAL = 10
        const val MAX_INTERVAL = 300
        const val HEARTBEAT_TIMEOUT = 15L
        const val DEBOUNCE_MILLIS = 2000L
    }
}
