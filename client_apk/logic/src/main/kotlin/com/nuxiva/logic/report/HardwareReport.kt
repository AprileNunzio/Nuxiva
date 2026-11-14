package com.nuxiva.logic.report

import com.nuxiva.logic.device.DeviceFacts
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

public object HardwareReport {
    private const val LIST_LIMIT = 12
    private const val SENSOR_LIMIT = 24
    private const val TEXT_LIMIT = 60

    public fun hardware(facts: DeviceFacts): JsonObject = buildJsonObject {
        put("cores", facts.cores.coerceIn(1, 512))
        put("ram_gb", Math.round(facts.ramMb / 1024.0 * 10.0) / 10.0)
        put("avx2", false)
        put("ir_camera", false)
        put("bluetooth", facts.hasBluetooth)
        put("arch", clean(facts.abi, 20))
        put("gpu", clean(facts.gpu))
        put("os", clean("android ${facts.androidRelease}"))
        put("model", clean("${facts.manufacturer} ${facts.model}"))
        put("cameras", strings(facts.cameras, LIST_LIMIT))
        put("audio_in", strings(if (facts.hasMicrophone) listOf("microphone") else emptyList(), LIST_LIMIT))
        put("audio_out", strings(listOf("speaker"), LIST_LIMIT))
        put("usb", JsonArray(emptyList()))
        put("soc", buildJsonObject {
            put("vendor", clean(facts.socVendor, 40))
            put("family", clean(facts.abi, 40))
            put("model", clean(facts.socModel, 80))
        })
        put("cpu_features", strings(if (facts.abi.startsWith("arm")) listOf("neon") else emptyList(), LIST_LIMIT))
        put("sensors", strings(facts.sensors, SENSOR_LIMIT))
        put("display", buildJsonObject {
            put("width", facts.display.widthPx)
            put("height", facts.display.heightPx)
            put("dpi", facts.display.densityDpi)
            put("hz", facts.display.refreshHz)
        })
        put("orientation", buildJsonObject {
            put("mode", facts.orientation.mode)
            put("rotation", facts.orientation.rotation)
            put("turn", facts.orientation.turn.wire)
        })
    }

    public fun scopes(facts: DeviceFacts, computeOffered: Boolean): List<String> {
        val found = linkedSetOf("telemetry.report", "audio.play", "display.render")
        if (facts.hasMicrophone) found += "audio.capture"
        if (facts.cameras.isNotEmpty()) found += "camera.stream"
        if (facts.sensors.isNotEmpty()) found += "sensor.read"
        if (computeOffered) found += "compute.lease"
        return found.sorted()
    }

    public fun announce(facts: DeviceFacts, computeOffered: Boolean): JsonObject = buildJsonObject {
        put("capabilities", buildJsonArray {
            scopes(facts, computeOffered).forEach { add(buildJsonObject { put("scope", it) }) }
        })
        put("hardware", buildJsonObject {
            put("cpu_cores", facts.cores.coerceAtLeast(0))
            put("ram_mb", facts.ramMb.coerceAtLeast(0))
        })
    }

    public fun clean(value: String, limit: Int = TEXT_LIMIT): String =
        value.filter { it.isLetterOrDigit() || it in " .,:;@()/+-'’" }.trim().take(limit)

    private fun strings(items: List<String>, limit: Int): JsonArray = JsonArray(
        items.map { clean(it) }.filter { it.isNotEmpty() }.distinct().take(limit).map { JsonPrimitive(it) },
    )
}
