package com.nuxiva.edge.compute

import android.content.Context
import android.content.SharedPreferences
import com.nuxiva.logic.compute.ShareSettings
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

class ShareSettingsStore(context: Context) {
    private val prefs: SharedPreferences = context.getSharedPreferences(FILE, Context.MODE_PRIVATE)
    private val state = MutableStateFlow(read())

    val settings: StateFlow<ShareSettings> = state.asStateFlow()

    @Synchronized
    fun update(change: (ShareSettings) -> ShareSettings) {
        val next = change(state.value)
        prefs.edit()
            .putBoolean(CONSENT, next.consent)
            .putBoolean(KILL, next.killSwitch)
            .putBoolean(CHARGING, next.requireCharging)
            .putInt(BATTERY, next.minBatteryPercent)
            .putInt(THERMAL, next.maxThermalStatus)
            .putInt(TEMP, next.maxBatteryTempC)
            .putBoolean(UNMETERED, next.unmeteredOnly)
            .putBoolean(REST, next.restOnly)
            .putInt(JOBS, next.maxJobs)
            .apply()
        state.value = next
    }

    private fun read(): ShareSettings {
        val defaults = ShareSettings()
        return ShareSettings(
            consent = prefs.getBoolean(CONSENT, defaults.consent),
            killSwitch = prefs.getBoolean(KILL, defaults.killSwitch),
            requireCharging = prefs.getBoolean(CHARGING, defaults.requireCharging),
            minBatteryPercent = prefs.getInt(BATTERY, defaults.minBatteryPercent),
            maxThermalStatus = prefs.getInt(THERMAL, defaults.maxThermalStatus),
            maxBatteryTempC = prefs.getInt(TEMP, defaults.maxBatteryTempC),
            unmeteredOnly = prefs.getBoolean(UNMETERED, defaults.unmeteredOnly),
            restOnly = prefs.getBoolean(REST, defaults.restOnly),
            maxJobs = prefs.getInt(JOBS, defaults.maxJobs),
        )
    }

    private companion object {
        const val FILE = "nuxiva_share_settings"
        const val CONSENT = "consent"
        const val KILL = "kill"
        const val CHARGING = "charging"
        const val BATTERY = "battery"
        const val THERMAL = "thermal"
        const val TEMP = "temp"
        const val UNMETERED = "unmetered"
        const val REST = "rest"
        const val JOBS = "jobs"
    }
}
