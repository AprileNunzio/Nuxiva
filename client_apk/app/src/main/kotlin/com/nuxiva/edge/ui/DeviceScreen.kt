package com.nuxiva.edge.ui

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.nuxiva.edge.R
import com.nuxiva.logic.compute.PowerSnapshot
import com.nuxiva.logic.device.DeviceFacts
import com.nuxiva.logic.device.OrientationState

@Composable
fun DeviceScreen(model: AppViewModel) {
    val facts by model.deviceFacts.collectAsState()
    val power by model.powerSnapshot.collectAsState()
    val orientation by model.orientation.collectAsState()
    LazyVerticalGrid(
        columns = GridCells.Adaptive(340.dp),
        contentPadding = PaddingValues(16.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        fullSpan("orientation") { OrientationCard(orientation) }
        val current = facts
        if (current == null) {
            fullSpan("loading") { InfoCard(stringResource(R.string.device_title)) { Text(stringResource(R.string.device_loading)) } }
        } else {
            fullSpan("identity") { IdentityCard(current) }
            fullSpan("resources") { ResourcesCard(current) }
            fullSpan("peripherals") { PeripheralsCard(current) }
        }
        power?.let { snapshot -> fullSpan("power") { PowerCard(snapshot) } }
    }
}

@Composable
private fun OrientationCard(state: OrientationState) {
    val angle by animateFloatAsState(targetValue = -state.rotation.toFloat(), label = "rotation")
    val color = MaterialTheme.colorScheme.primary
    InfoCard(stringResource(R.string.orientation_title)) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(16.dp), verticalAlignment = Alignment.CenterVertically) {
            Canvas(Modifier.height(96.dp).weight(0.35f)) {
                val width = size.height * 0.5f
                val height = size.height * 0.85f
                val origin = Offset((size.width - width) / 2f, (size.height - height) / 2f)
                rotate(angle, pivot = center) {
                    drawRoundRect(color, origin, Size(width, height), CornerRadius(12.dp.toPx()), style = Stroke(width = 3.dp.toPx()))
                    drawLine(color, Offset(center.x - width * 0.15f, origin.y + 10.dp.toPx()), Offset(center.x + width * 0.15f, origin.y + 10.dp.toPx()), strokeWidth = 3.dp.toPx())
                }
            }
            androidx.compose.foundation.layout.Column(Modifier.weight(0.65f), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                KeyValue(stringResource(R.string.orientation_mode), stringResource(if (state.mode == "landscape") R.string.mode_landscape else R.string.mode_portrait))
                KeyValue(stringResource(R.string.orientation_rotation), "${state.rotation}°")
                KeyValue(stringResource(R.string.orientation_turn), stringResource(turnLabel(state.turn)))
            }
        }
        Text(stringResource(R.string.orientation_hint), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.secondary)
    }
}

@Composable
private fun IdentityCard(facts: DeviceFacts) {
    InfoCard(stringResource(R.string.device_title)) {
        KeyValue(stringResource(R.string.field_model), "${facts.manufacturer} ${facts.model}")
        KeyValue(stringResource(R.string.field_android), "${facts.androidRelease} (API ${facts.sdk})")
        KeyValue(stringResource(R.string.field_soc), listOf(facts.socVendor, facts.socModel).filter { it.isNotBlank() }.joinToString(" "))
        KeyValue(stringResource(R.string.field_abi), facts.abi)
    }
}

@Composable
private fun ResourcesCard(facts: DeviceFacts) {
    InfoCard(stringResource(R.string.resources_title)) {
        KeyValue(stringResource(R.string.field_cpu), stringResource(R.string.value_cores, facts.cores))
        KeyValue(stringResource(R.string.field_ram), "%.1f GB".format(facts.ramMb / 1024.0))
        KeyValue(stringResource(R.string.field_gpu), facts.gpu)
        KeyValue(
            stringResource(R.string.field_display),
            "${facts.display.widthPx}×${facts.display.heightPx} · ${facts.display.densityDpi} dpi · ${facts.display.refreshHz} Hz",
        )
    }
}

@Composable
private fun PeripheralsCard(facts: DeviceFacts) {
    InfoCard(stringResource(R.string.peripherals_title)) {
        KeyValue(stringResource(R.string.field_microphone), stringResource(if (facts.hasMicrophone) R.string.yes else R.string.no))
        KeyValue(stringResource(R.string.field_bluetooth), stringResource(if (facts.hasBluetooth) R.string.yes else R.string.no))
        KeyValue(stringResource(R.string.field_cameras), facts.cameras.joinToString(", "))
        KeyValue(stringResource(R.string.field_sensors), facts.sensors.joinToString(", "))
    }
}

@Composable
private fun PowerCard(power: PowerSnapshot) {
    InfoCard(stringResource(R.string.power_title)) {
        KeyValue(stringResource(R.string.field_battery), "${power.batteryPercent}%")
        KeyValue(stringResource(R.string.field_charging), stringResource(if (power.charging) R.string.yes else R.string.no))
        KeyValue(stringResource(R.string.field_temperature), power.batteryTempDeciC?.let { "%.1f °C".format(it / 10.0) }.orEmpty())
        KeyValue(stringResource(R.string.field_thermal), power.thermalStatus?.toString().orEmpty())
        KeyValue(stringResource(R.string.field_network), stringResource(if (power.unmetered) R.string.network_unmetered else R.string.network_metered))
        KeyValue(stringResource(R.string.field_screen), stringResource(if (power.screenOn) R.string.screen_on else R.string.screen_off))
    }
}
