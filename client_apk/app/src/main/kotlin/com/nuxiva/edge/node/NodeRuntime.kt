package com.nuxiva.edge.node

import android.util.Log
import com.nuxiva.edge.compute.ComputeRelay
import com.nuxiva.edge.compute.OllamaProbe
import com.nuxiva.edge.compute.ShareSettingsStore
import com.nuxiva.edge.device.OrientationMonitor
import com.nuxiva.edge.device.PowerMonitor
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineExceptionHandler
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

class NodeRuntime(
    private val store: ProfileStore,
    private val reports: ReportBuilder,
    private val power: PowerMonitor,
    private val ollama: OllamaProbe,
    private val shareSettings: ShareSettingsStore,
    private val orientation: OrientationMonitor,
    private val multicast: MulticastGuard,
) {
    private val handler = CoroutineExceptionHandler { _, error -> Log.e(TAG, "Uncaught runtime error", error) }
    private var scope: CoroutineScope? = null
    private val workers = mutableMapOf<String, Pair<NodeProfile, Job>>()
    private val linkState = MutableStateFlow<Map<String, LinkState>>(emptyMap())
    private val eventFlow = MutableSharedFlow<RuntimeEvent>(extraBufferCapacity = 8)
    private val runningState = MutableStateFlow(false)

    val links: StateFlow<Map<String, LinkState>> = linkState.asStateFlow()
    val events: SharedFlow<RuntimeEvent> = eventFlow.asSharedFlow()
    val running: StateFlow<Boolean> = runningState.asStateFlow()

    @Synchronized
    fun start() {
        if (scope != null) return
        val created = CoroutineScope(SupervisorJob() + Dispatchers.Default + handler)
        scope = created
        orientation.start()
        multicast.acquire()
        runningState.value = true
        created.launch { store.profiles.collect { reconcile(it) } }
    }

    @Synchronized
    fun stop() {
        if (scope == null) return
        scope?.cancel()
        scope = null
        workers.clear()
        orientation.stop()
        multicast.release()
        linkState.value = emptyMap()
        runningState.value = false
    }

    @Synchronized
    private fun reconcile(profiles: List<NodeProfile>) {
        val active = scope ?: return
        val wanted = profiles.filter { it.enabled }.associateBy { it.nodeId }
        workers.keys.filter { id -> wanted[id] == null || wanted[id] != workers[id]?.first }.forEach { id ->
            workers.remove(id)?.second?.cancel()
            if (wanted[id] == null) linkState.update { it - id }
        }
        wanted.values.filter { it.nodeId !in workers }.forEach { profile ->
            workers[profile.nodeId] = profile to active.launch { supervise(profile) }
        }
    }

    private suspend fun supervise(profile: NodeProfile) {
        val http = NodeHttp(profile)
        val relay = ComputeRelay(http, { shareSettings.settings.value }, power, ollama)
        val loop = HeartbeatLoop(
            profile, http, reports, orientation,
            sharing = relay::sharing,
            computeOffered = { shareSettings.settings.value.let { it.consent && !it.killSwitch } },
            onState = { state -> linkState.update { it + (profile.nodeId to state) } },
            onEvent = { eventFlow.tryEmit(it) },
        )
        kotlinx.coroutines.coroutineScope {
            launch { guarded("heartbeat ${profile.nodeId}") { loop.run() } }
            launch { guarded("compute ${profile.nodeId}") { relay.run() } }
            launch {
                guarded("peer ${profile.nodeId}") {
                    PeerWatch(
                        profile,
                        isOnline = { linkState.value[profile.nodeId] is LinkState.Online },
                        moveTo = { url -> store.update(profile.nodeId) { it.copy(server = url) } },
                    ).run()
                }
            }
        }
    }

    private suspend fun guarded(label: String, block: suspend () -> Unit) {
        var attempt = 0
        while (true) {
            try {
                block()
                return
            } catch (error: CancellationException) {
                throw error
            } catch (error: Exception) {
                attempt += 1
                Log.e(TAG, "$label crashed, restarting (attempt $attempt)", error)
                delay(minOf(60_000L, 2_000L * attempt))
            }
        }
    }

    private companion object {
        const val TAG = "NuxivaRuntime"
    }
}
