package com.nuxiva.edge.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.nuxiva.edge.BuildConfig
import com.nuxiva.edge.R

@Composable
fun SettingsScreen(model: AppViewModel, onPair: () -> Unit) {
    val hub by model.hubPrefs.collectAsState()
    val running by model.running.collectAsState()
    val profiles by model.profiles.collectAsState()
    LazyVerticalGrid(
        columns = GridCells.Adaptive(340.dp),
        contentPadding = PaddingValues(16.dp),
        horizontalArrangement = Arrangement.spacedBy(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        fullSpan("hub") {
            InfoCard(stringResource(R.string.hub_title)) {
                ToggleRow(stringResource(R.string.settings_hub_launch), hub.openOnLaunch) { value -> model.updateHub { it.copy(openOnLaunch = value) } }
                ToggleRow(stringResource(R.string.hub_mic), hub.microphone) { value -> model.updateHub { it.copy(microphone = value) } }
                ToggleRow(stringResource(R.string.hub_camera), hub.camera) { value -> model.updateHub { it.copy(camera = value) } }
                ToggleRow(stringResource(R.string.hub_native_location), hub.location) { value -> model.updateHub { it.copy(location = value) } }
                ToggleRow(stringResource(R.string.hub_server_page), hub.serverPage) { value -> model.updateHub { it.copy(serverPage = value) } }
                Text(stringResource(R.string.hub_privacy_hint), style = MaterialTheme.typography.bodySmall, color = LocalTokens.current.muted)
            }
        }
        fullSpan("service") {
            InfoCard(stringResource(R.string.service_title)) {
                ToggleRow(stringResource(if (running) R.string.service_on else R.string.service_off), running) { model.setService(it) }
                Text(stringResource(R.string.service_hint), style = MaterialTheme.typography.bodySmall, color = LocalTokens.current.muted)
            }
        }
        fullSpan("pair") {
            InfoCard(stringResource(R.string.settings_pair_title)) {
                Text(stringResource(R.string.settings_pair_body, profiles.size), style = MaterialTheme.typography.bodyMedium)
                PrimaryAction(stringResource(R.string.nodes_add), onPair)
            }
        }
        fullSpan("privacy") {
            InfoCard(stringResource(R.string.settings_privacy_title)) {
                Text(stringResource(R.string.settings_privacy_body), style = MaterialTheme.typography.bodyMedium)
            }
        }
        fullSpan("about") {
            InfoCard(stringResource(R.string.settings_about_title)) {
                KeyValue(stringResource(R.string.settings_version), BuildConfig.VERSION_NAME)
            }
        }
    }
}
