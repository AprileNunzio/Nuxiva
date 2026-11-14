package com.nuxiva.edge.core

import android.app.Application
import com.nuxiva.edge.compute.OllamaProbe
import com.nuxiva.edge.compute.ShareSettingsStore
import com.nuxiva.edge.device.DeviceInspector
import com.nuxiva.edge.device.OrientationMonitor
import com.nuxiva.edge.device.PowerMonitor
import com.nuxiva.edge.node.Enroller
import com.nuxiva.edge.node.KeystoreCipher
import com.nuxiva.edge.node.NodeRuntime
import com.nuxiva.edge.node.ProfileStore
import com.nuxiva.edge.node.ReportBuilder

class AppGraph(app: Application) {
    val profiles = ProfileStore(app, KeystoreCipher())
    val shareSettings = ShareSettingsStore(app)
    val hub = com.nuxiva.edge.hub.HubSettings(app)
    val orientation = OrientationMonitor(app)
    val power = PowerMonitor(app)
    val ollama = OllamaProbe()
    val inspector = DeviceInspector(app, orientation)
    val enroller = Enroller(profiles)
    private val reports = ReportBuilder(app, inspector, power, ollama)
    val runtime = NodeRuntime(profiles, reports, power, ollama, shareSettings, orientation)
}
