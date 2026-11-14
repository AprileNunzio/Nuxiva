package com.nuxiva.logic

import com.nuxiva.logic.device.DeviceFacts
import com.nuxiva.logic.device.DisplayFacts
import com.nuxiva.logic.device.OrientationState
import com.nuxiva.logic.device.Turn
import com.nuxiva.logic.report.HardwareReport
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class ReportTest {
    private val facts = DeviceFacts(
        manufacturer = "Google", model = "Pixel 8 <script>", socVendor = "Google", socModel = "Tensor G3", abi = "arm64-v8a",
        cores = 9, ramMb = 7_900, gpu = "Mali-G715", androidRelease = "14", sdk = 34,
        sensors = listOf("Accelerometer", "Gyroscope", "Accelerometer"), cameras = listOf("back", "front"),
        hasMicrophone = true, hasBluetooth = true, display = DisplayFacts(1080, 2400, 420, 120),
        orientation = OrientationState("portrait", 0, Turn.None),
    )

    @Test
    fun hardwareIsSanitisedAndShapedForTheServer() {
        val hardware: JsonObject = HardwareReport.hardware(facts)
        assertEquals("Google Pixel 8 script", hardware.getValue("model").jsonPrimitive.content)
        assertEquals("7.7", hardware.getValue("ram_gb").jsonPrimitive.content)
        assertEquals(2, hardware.getValue("sensors").jsonArray.size)
        assertEquals("arm64-v8a", hardware.getValue("arch").jsonPrimitive.content)
        assertEquals("portrait", hardware.getValue("orientation").jsonObject.getValue("mode").jsonPrimitive.content)
        assertEquals(JsonArray(emptyList()), hardware.getValue("usb"))
    }

    @Test
    fun scopesReflectOnlyWhatTheDeviceHasAndTheComputeOffer() {
        val plain = HardwareReport.scopes(facts, false)
        assertTrue("compute.lease" !in plain)
        assertTrue("audio.capture" in plain && "camera.stream" in plain && "sensor.read" in plain)
        assertTrue("compute.lease" in HardwareReport.scopes(facts, true))
        val bare = HardwareReport.scopes(facts.copy(hasMicrophone = false, cameras = emptyList(), sensors = emptyList()), false)
        assertEquals(listOf("audio.play", "display.render", "telemetry.report"), bare)
    }

    @Test
    fun announceCarriesCoresAndRam() {
        val announce = HardwareReport.announce(facts, false)
        assertEquals("9", announce.getValue("hardware").jsonObject.getValue("cpu_cores").jsonPrimitive.content)
    }
}
