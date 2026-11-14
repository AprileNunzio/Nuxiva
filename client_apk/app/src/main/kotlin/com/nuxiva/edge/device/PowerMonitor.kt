package com.nuxiva.edge.device

import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.BatteryManager
import android.os.Build
import android.os.PowerManager
import com.nuxiva.logic.compute.PowerSnapshot

class PowerMonitor(private val context: Context) {
    private val power = context.getSystemService(PowerManager::class.java)
    private val connectivity = context.getSystemService(ConnectivityManager::class.java)

    fun snapshot(): PowerSnapshot {
        val battery = context.registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED))
        val level = battery?.getIntExtra(BatteryManager.EXTRA_LEVEL, -1) ?: -1
        val scale = battery?.getIntExtra(BatteryManager.EXTRA_SCALE, -1) ?: -1
        val percent = if (level >= 0 && scale > 0) level * 100 / scale else 0
        val plugged = (battery?.getIntExtra(BatteryManager.EXTRA_PLUGGED, 0) ?: 0) != 0
        val temperature = battery?.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, Int.MIN_VALUE)?.takeIf { it != Int.MIN_VALUE }
        val thermal = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) power.currentThermalStatus else null
        return PowerSnapshot(percent, plugged, thermal, temperature, unmetered(), power.isInteractive)
    }

    fun batteryTempCelsius(): Double? =
        context.registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED))
            ?.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, Int.MIN_VALUE)?.takeIf { it != Int.MIN_VALUE }?.let { it / 10.0 }

    private fun unmetered(): Boolean {
        val network = connectivity.activeNetwork ?: return false
        val capabilities = connectivity.getNetworkCapabilities(network) ?: return false
        return capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_NOT_METERED) &&
            capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)
    }
}
