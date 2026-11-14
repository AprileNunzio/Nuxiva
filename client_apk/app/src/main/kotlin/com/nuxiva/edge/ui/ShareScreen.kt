package com.nuxiva.edge.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Slider
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.nuxiva.edge.R
import com.nuxiva.edge.compute.OllamaState
import com.nuxiva.logic.compute.PowerSnapshot
import com.nuxiva.logic.compute.ShareDecision
import com.nuxiva.logic.compute.SharePolicy
import com.nuxiva.logic.compute.ShareSettings

@Composable
fun ShareScreen(model: AppViewModel) {
    val settings by model.share.collectAsState()
    val power by model.powerSnapshot.collectAsState()
    val ollama by model.ollamaState.collectAsState()
    LazyVerticalGrid(
        columns = GridCells.Adaptive(340.dp),
        contentPadding = PaddingValues(16.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        fullSpan("status") { StatusCard(settings, power, ollama, model) }
        fullSpan("conditions") { ConditionsCard(settings, model) }
        fullSpan("engine") { EngineCard(ollama) }
    }
}

@Composable
private fun StatusCard(settings: ShareSettings, power: PowerSnapshot?, ollama: OllamaState, model: AppViewModel) {
    val decision = power?.let { SharePolicy.decide(settings, it) }
    InfoCard(stringResource(R.string.share_title)) {
        Text(stringResource(R.string.share_intro))
        power?.let { Stat(stringResource(R.string.field_battery), "${it.batteryPercent}%", fraction = it.batteryPercent / 100f, marker = settings.minBatteryPercent / 100f) }
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Text(stringResource(R.string.share_consent), modifier = Modifier.weight(1f), style = MaterialTheme.typography.bodyLarge)
            Switch(checked = settings.consent, onCheckedChange = { value -> model.updateShare { it.copy(consent = value) } })
        }
        val message = when {
            decision is ShareDecision.Denied -> stringResource(denyLabel(decision.reason))
            decision == ShareDecision.Allowed && !ollama.available -> stringResource(R.string.share_waiting_engine)
            decision == ShareDecision.Allowed -> stringResource(R.string.share_active)
            else -> stringResource(R.string.device_loading)
        }
        Text(message, style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.primary)
        if (settings.killSwitch) {
            PrimaryAction(stringResource(R.string.share_kill_reset), { model.updateShare { it.copy(killSwitch = false) } })
        } else {
            PrimaryAction(stringResource(R.string.share_kill), { model.updateShare { it.copy(killSwitch = true) } }, danger = true)
        }
        Text(stringResource(R.string.share_trust_hint), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.secondary)
    }
}

@Composable
private fun ConditionsCard(settings: ShareSettings, model: AppViewModel) {
    InfoCard(stringResource(R.string.conditions_title)) {
        ToggleRow(stringResource(R.string.cond_charging), settings.requireCharging) { v -> model.updateShare { it.copy(requireCharging = v) } }
        ToggleRow(stringResource(R.string.cond_unmetered), settings.unmeteredOnly) { v -> model.updateShare { it.copy(unmeteredOnly = v) } }
        ToggleRow(stringResource(R.string.cond_rest), settings.restOnly) { v -> model.updateShare { it.copy(restOnly = v) } }
        Text(stringResource(R.string.cond_battery, settings.minBatteryPercent), style = MaterialTheme.typography.bodyMedium)
        Slider(
            value = settings.minBatteryPercent.toFloat(),
            onValueChange = { v -> model.updateShare { it.copy(minBatteryPercent = v.toInt().coerceIn(10, 90)) } },
            valueRange = 10f..90f,
            steps = 7,
        )
        Text(stringResource(R.string.cond_jobs, settings.jobLimit), style = MaterialTheme.typography.bodyMedium)
        Slider(
            value = settings.jobLimit.toFloat(),
            onValueChange = { v -> model.updateShare { it.copy(maxJobs = v.toInt().coerceIn(ShareSettings.MIN_JOBS, ShareSettings.MAX_JOBS)) } },
            valueRange = ShareSettings.MIN_JOBS.toFloat()..ShareSettings.MAX_JOBS.toFloat(),
            steps = ShareSettings.MAX_JOBS - ShareSettings.MIN_JOBS - 1,
        )
        Text(stringResource(R.string.cond_jobs_hint), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.secondary)
        Text(stringResource(R.string.cond_thermal), style = MaterialTheme.typography.bodyMedium)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            listOf(0 to R.string.thermal_none, 1 to R.string.thermal_light, 2 to R.string.thermal_moderate).forEach { (level, label) ->
                FilterChip(
                    selected = settings.maxThermalStatus == level,
                    onClick = { model.updateShare { it.copy(maxThermalStatus = level) } },
                    label = { Text(stringResource(label)) },
                )
            }
        }
    }
}

@Composable
private fun EngineCard(ollama: OllamaState) {
    InfoCard(stringResource(R.string.engine_title)) {
        Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
            KeyValue(stringResource(R.string.engine_status), stringResource(if (ollama.available) R.string.engine_found else R.string.engine_missing))
            if (ollama.available) {
                KeyValue(stringResource(R.string.engine_version), ollama.version)
                KeyValue(stringResource(R.string.engine_models), ollama.models.joinToString(", ") { it.name })
            } else {
                Text(stringResource(R.string.engine_hint), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.secondary)
            }
        }
    }
}
