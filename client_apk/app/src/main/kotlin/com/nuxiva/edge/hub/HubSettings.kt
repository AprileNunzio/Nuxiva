package com.nuxiva.edge.hub

import android.content.Context
import android.content.pm.PackageManager
import android.content.res.Configuration
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

data class HubPrefs(
    val microphone: Boolean = false,
    val camera: Boolean = false,
    val openOnLaunch: Boolean = false,
)

class HubSettings(private val context: Context) {
    private val prefs = context.getSharedPreferences(FILE, Context.MODE_PRIVATE)
    private val state = MutableStateFlow(read())

    val settings: StateFlow<HubPrefs> = state.asStateFlow()

    @Synchronized
    fun update(change: (HubPrefs) -> HubPrefs) {
        val next = change(state.value)
        prefs.edit()
            .putBoolean(MICROPHONE, next.microphone)
            .putBoolean(CAMERA, next.camera)
            .putBoolean(LAUNCH, next.openOnLaunch)
            .apply()
        state.value = next
    }

    private fun read(): HubPrefs = HubPrefs(
        microphone = prefs.getBoolean(MICROPHONE, false),
        camera = prefs.getBoolean(CAMERA, false),
        openOnLaunch = prefs.getBoolean(LAUNCH, television()),
    )

    fun television(): Boolean =
        context.packageManager.hasSystemFeature(PackageManager.FEATURE_LEANBACK) ||
            (context.resources.configuration.uiMode and Configuration.UI_MODE_TYPE_MASK) == Configuration.UI_MODE_TYPE_TELEVISION

    private companion object {
        const val FILE = "nuxiva_hub"
        const val MICROPHONE = "microphone"
        const val CAMERA = "camera"
        const val LAUNCH = "launch"
    }
}
