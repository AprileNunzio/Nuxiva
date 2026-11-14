package com.nuxiva.edge.node

import android.content.Context
import android.os.Build
import android.os.Environment
import android.os.StatFs
import android.os.SystemClock
import com.nuxiva.edge.BuildConfig
import com.nuxiva.edge.compute.OllamaProbe
import com.nuxiva.edge.device.DeviceInspector
import com.nuxiva.edge.device.PowerMonitor
import com.nuxiva.logic.report.HardwareReport
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

class ReportBuilder(
    private val context: Context,
    private val inspector: DeviceInspector,
    private val power: PowerMonitor,
    private val ollama: OllamaProbe,
) {

    fun build(sharing: Boolean, computeOffered: Boolean, adapted: Boolean): JsonObject {
        val facts = inspector.facts()
        val oll = ollama.read()
        return buildJsonObject {
            put("version", BuildConfig.VERSION_NAME)
            put("hostname", HardwareReport.clean(Build.MODEL.orEmpty(), 60))
            put("agent", "android")
            put("hardware", HardwareReport.hardware(facts))
            put("announce", HardwareReport.announce(facts, computeOffered))
            put("capabilities", capabilities(facts.hasMicrophone, facts.cameras.isNotEmpty(), facts.sensors.isNotEmpty(), computeOffered))
            put("metrics", metrics(facts.ramMb))
            put("compute", buildJsonObject {
                put("ollama", buildJsonObject {
                    put("available", oll.available)
                    put("shared", sharing && oll.available)
                    put("version", oll.version)
                    put("models", JsonArray(oll.models.map { model(it.name, it.sizeGb) }))
                    put("running", JsonArray(oll.running.map { model(it.name, it.sizeGb) }))
                })
            })
            if (adapted) put("adapted", true)
        }
    }

    private fun capabilities(microphone: Boolean, camera: Boolean, sensors: Boolean, compute: Boolean): JsonArray {
        val names = buildList {
            if (microphone) add("microphone")
            if (camera) add("camera")
            if (sensors) add("sensors")
            add("display")
            if (compute) add("compute")
        }
        return JsonArray(names.map { JsonPrimitive(it) })
    }

    private fun metrics(totalRamMb: Long): JsonObject = buildJsonObject {
        if (totalRamMb > 0) {
            val used = (totalRamMb - inspector.availableRamMb()).coerceAtLeast(0)
            put("ram", Math.round(used * 1000.0 / totalRamMb) / 10.0)
        }
        power.batteryTempCelsius()?.let { put("temp", it) }
        put("uptime", SystemClock.elapsedRealtime() / 1000L)
        val stat = StatFs(Environment.getDataDirectory().path)
        if (stat.blockCountLong > 0) {
            val used = stat.blockCountLong - stat.availableBlocksLong
            put("disk", Math.round(used * 1000.0 / stat.blockCountLong) / 10.0)
        }
    }

    private fun model(name: String, sizeGb: Double): JsonObject = buildJsonObject {
        put("name", name)
        put("size_gb", sizeGb)
    }
}
