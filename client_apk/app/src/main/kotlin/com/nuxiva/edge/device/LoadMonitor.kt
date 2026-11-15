package com.nuxiva.edge.device

import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.net.TrafficStats
import android.os.BatteryManager
import android.os.SystemClock
import java.io.File
import kotlin.math.abs

data class Throughput(val rxKbps: Double, val txKbps: Double)

class LoadMonitor(private val context: Context) {
    private val battery = context.getSystemService(BatteryManager::class.java)
    private val cores = Runtime.getRuntime().availableProcessors().coerceAtLeast(1)
    private var lastCpu: LongArray? = null
    private var lastRx = TrafficStats.getTotalRxBytes()
    private var lastTx = TrafficStats.getTotalTxBytes()
    private var lastTraffic = SystemClock.elapsedRealtime()

    @Synchronized
    fun cpuPercent(): Double? {
        val current = readStat()
        if (current != null) {
            val previous = lastCpu
            lastCpu = current
            if (previous != null) {
                val total = current[0] - previous[0]
                val idle = current[1] - previous[1]
                if (total > 0) return round1(((total - idle) * 100.0 / total).coerceIn(0.0, 100.0))
            }
            return null
        }
        return loadAverage()
    }

    @Synchronized
    fun throughput(): Throughput? {
        val rx = TrafficStats.getTotalRxBytes()
        val tx = TrafficStats.getTotalTxBytes()
        val now = SystemClock.elapsedRealtime()
        val elapsed = now - lastTraffic
        val previousRx = lastRx
        val previousTx = lastTx
        lastRx = rx
        lastTx = tx
        lastTraffic = now
        if (rx == TrafficStats.UNSUPPORTED.toLong() || tx == TrafficStats.UNSUPPORTED.toLong()) return null
        if (previousRx == TrafficStats.UNSUPPORTED.toLong() || elapsed < MIN_WINDOW_MILLIS) return null
        val seconds = elapsed / 1000.0
        return Throughput(
            round1(((rx - previousRx).coerceAtLeast(0) * 8.0 / 1000.0) / seconds),
            round1(((tx - previousTx).coerceAtLeast(0) * 8.0 / 1000.0) / seconds),
        )
    }

    fun powerWatts(): Double? {
        val raw = battery.getLongProperty(BatteryManager.BATTERY_PROPERTY_CURRENT_NOW)
        if (raw == Long.MIN_VALUE || raw == 0L) return null
        val volts = context.registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED))
            ?.getIntExtra(BatteryManager.EXTRA_VOLTAGE, 0)?.takeIf { it > 0 } ?: return null
        val microAmps = if (abs(raw) < MILLIAMP_LIMIT) abs(raw) * 1000.0 else abs(raw).toDouble()
        val watts = microAmps / 1_000_000.0 * (volts / 1000.0)
        return if (watts in 0.0..MAX_WATTS) round2(watts) else null
    }

    private fun readStat(): LongArray? = try {
        val line = File("/proc/stat").bufferedReader().use { it.readLine() }
        val parts = line?.trim()?.split(Regex("\\s+"))?.drop(1)?.mapNotNull { it.toLongOrNull() }.orEmpty()
        if (parts.size < 5) null else longArrayOf(parts.take(8).sum(), parts[3] + parts[4])
    } catch (ignored: java.io.IOException) {
        null
    } catch (ignored: SecurityException) {
        null
    }

    private fun loadAverage(): Double? = try {
        val first = File("/proc/loadavg").bufferedReader().use { it.readLine() }?.substringBefore(' ')?.toDoubleOrNull()
        first?.let { round1((it / cores * 100.0).coerceIn(0.0, 100.0)) }
    } catch (ignored: java.io.IOException) {
        null
    } catch (ignored: SecurityException) {
        null
    }

    private fun round1(value: Double) = Math.round(value * 10.0) / 10.0

    private fun round2(value: Double) = Math.round(value * 100.0) / 100.0

    private companion object {
        const val MIN_WINDOW_MILLIS = 1000L
        const val MILLIAMP_LIMIT = 20_000L
        const val MAX_WATTS = 200.0
    }
}
