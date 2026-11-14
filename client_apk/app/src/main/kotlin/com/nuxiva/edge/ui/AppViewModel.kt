package com.nuxiva.edge.ui

import android.app.Application
import android.os.Build
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.nuxiva.edge.compute.OllamaState
import com.nuxiva.edge.core.graph
import com.nuxiva.edge.node.EnrollmentFailure
import com.nuxiva.edge.node.RuntimeEvent
import com.nuxiva.edge.service.NodeService
import com.nuxiva.logic.compute.PowerSnapshot
import com.nuxiva.logic.compute.ShareSettings
import com.nuxiva.logic.device.DeviceFacts
import com.nuxiva.logic.enroll.EnrollmentException
import com.nuxiva.logic.enroll.EnrollmentParser
import com.nuxiva.logic.enroll.EnrollmentPayload
import com.nuxiva.logic.net.PinnedTrust
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

sealed interface EnrollUi {
    data object Idle : EnrollUi
    data class Review(val payload: EnrollmentPayload, val pinShort: String) : EnrollUi
    data object Working : EnrollUi
    data class Failed(val code: String) : EnrollUi
    data class Done(val nodeId: String) : EnrollUi
}

class AppViewModel(application: Application) : AndroidViewModel(application) {
    private val graph = application.graph
    private val facts = MutableStateFlow<DeviceFacts?>(null)
    private val power = MutableStateFlow<PowerSnapshot?>(null)
    private val ollama = MutableStateFlow(OllamaState.Absent)
    private val enrollState = MutableStateFlow<EnrollUi>(EnrollUi.Idle)

    val profiles = graph.profiles.profiles
    val loadFailure = graph.profiles.loadFailure
    val links = graph.runtime.links
    val running = graph.runtime.running
    val share: StateFlow<ShareSettings> = graph.shareSettings.settings
    val orientation = graph.orientation.current
    val hubPrefs = graph.hub.settings
    val events: SharedFlow<RuntimeEvent> = graph.runtime.events
    val deviceFacts: StateFlow<DeviceFacts?> = facts.asStateFlow()
    val powerSnapshot: StateFlow<PowerSnapshot?> = power.asStateFlow()
    val ollamaState: StateFlow<OllamaState> = ollama.asStateFlow()
    val enroll: StateFlow<EnrollUi> = enrollState.asStateFlow()

    init {
        graph.orientation.start()
    }

    override fun onCleared() {
        graph.orientation.stop()
    }

    suspend fun refresh() {
        withContext(Dispatchers.IO) {
            facts.value = graph.inspector.facts()
            power.value = graph.power.snapshot()
            ollama.value = graph.ollama.read()
        }
    }

    fun offerEnrollment(raw: String) {
        enrollState.value = try {
            val payload = EnrollmentParser.parse(raw, System.currentTimeMillis() / 1000L)
            EnrollUi.Review(payload, PinnedTrust.short(payload.pin))
        } catch (error: EnrollmentException) {
            EnrollUi.Failed(error.code)
        }
    }

    fun offerCode(server: String, code: String) {
        val target: String
        val digits: String
        try {
            target = EnrollmentParser.normalizeServerInput(server)
            digits = EnrollmentParser.normalizeCode(code)
        } catch (error: EnrollmentException) {
            enrollState.value = EnrollUi.Failed(error.code)
            return
        }
        enrollState.value = EnrollUi.Working
        viewModelScope.launch {
            enrollState.value = try {
                val payload = graph.enroller.payloadForCode(target, digits)
                EnrollUi.Review(payload, PinnedTrust.short(payload.pin))
            } catch (error: EnrollmentFailure) {
                EnrollUi.Failed(error.code)
            }
        }
    }

    fun confirmEnrollment(name: String) {
        val review = enrollState.value as? EnrollUi.Review ?: return
        enrollState.value = EnrollUi.Working
        viewModelScope.launch {
            enrollState.value = try {
                val profile = graph.enroller.enroll(review.payload, name)
                NodeService.start(getApplication())
                EnrollUi.Done(profile.nodeId)
            } catch (error: EnrollmentFailure) {
                EnrollUi.Failed(error.code)
            }
        }
    }

    fun resetEnrollment() {
        enrollState.value = EnrollUi.Idle
    }

    fun remove(nodeId: String) {
        graph.profiles.remove(nodeId)
        android.webkit.CookieManager.getInstance().removeAllCookies(null)
        if (graph.profiles.profiles.value.none { it.enabled }) NodeService.stop(getApplication())
    }

    fun setEnabled(nodeId: String, enabled: Boolean) {
        graph.profiles.update(nodeId) { it.copy(enabled = enabled) }
        if (enabled && !running.value) NodeService.start(getApplication())
    }

    fun setService(on: Boolean) {
        if (on) NodeService.start(getApplication()) else NodeService.stop(getApplication())
    }

    fun ensureService() {
        if (graph.profiles.profiles.value.any { it.enabled } && !running.value && !com.nuxiva.edge.service.ServiceSwitch.userStopped(getApplication())) {
            NodeService.start(getApplication())
        }
    }

    fun updateHub(change: (com.nuxiva.edge.hub.HubPrefs) -> com.nuxiva.edge.hub.HubPrefs) = graph.hub.update(change)

    fun updateShare(change: (ShareSettings) -> ShareSettings) = graph.shareSettings.update(change)

    fun shouldOpenHub(): Boolean =
        graph.hub.settings.value.openOnLaunch && graph.profiles.profiles.value.any { it.enabled }

    fun defaultNodeName(): String = Build.MODEL.orEmpty()
}
