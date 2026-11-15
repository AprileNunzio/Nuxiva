package com.nuxiva.edge.hub

import android.content.Context
import android.content.pm.PackageManager
import android.content.res.Configuration
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

enum class HubLayout { Auto, Widgets, Audio }

data class HubPrefs(
    val microphone: Boolean = true,
    val camera: Boolean = true,
    val location: Boolean = true,
    val openOnLaunch: Boolean = true,
    val serverPage: Boolean = false,
    val layout: HubLayout = HubLayout.Auto,
    val permissionsAsked: Boolean = false,
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
            .putBoolean(LOCATION, next.location)
            .putBoolean(LAUNCH, next.openOnLaunch)
            .putBoolean(SERVER_PAGE, next.serverPage)
            .putString(LAYOUT, next.layout.name)
            .putBoolean(ASKED, next.permissionsAsked)
            .apply()
        state.value = next
    }

    private fun read(): HubPrefs = HubPrefs(
        microphone = prefs.getBoolean(MICROPHONE, true),
        camera = prefs.getBoolean(CAMERA, true),
        location = prefs.getBoolean(LOCATION, true),
        openOnLaunch = prefs.getBoolean(LAUNCH, true),
        serverPage = prefs.getBoolean(SERVER_PAGE, television()),
        layout = prefs.getString(LAYOUT, null)?.let { name -> HubLayout.entries.firstOrNull { it.name == name } } ?: HubLayout.Auto,
        permissionsAsked = prefs.getBoolean(ASKED, false),
    )

    fun television(): Boolean =
        context.packageManager.hasSystemFeature(PackageManager.FEATURE_LEANBACK) ||
            (context.resources.configuration.uiMode and Configuration.UI_MODE_TYPE_MASK) == Configuration.UI_MODE_TYPE_TELEVISION

    private companion object {
        const val FILE = "nuxiva_hub"
        const val MICROPHONE = "microphone"
        const val CAMERA = "camera"
        const val LOCATION = "location"
        const val LAUNCH = "launch"
        const val SERVER_PAGE = "server_page"
        const val LAYOUT = "layout"
        const val ASKED = "permissions_asked"
    }
}
