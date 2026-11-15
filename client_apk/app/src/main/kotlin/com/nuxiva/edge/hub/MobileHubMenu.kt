package com.nuxiva.edge.hub

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.nuxiva.edge.R
import com.nuxiva.edge.ui.LocalTokens
import com.nuxiva.edge.ui.ToggleRow

@Composable
fun MobileHubMenu(
    prefs: HubPrefs,
    missingPermissions: Boolean,
    onChange: ((HubPrefs) -> HubPrefs) -> Unit,
    onRequestPermissions: () -> Unit,
    onOpenApp: () -> Unit,
    onDismiss: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.hub_menu_title)) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text(stringResource(R.string.hub_layout_title), style = MaterialTheme.typography.labelMedium, color = LocalTokens.current.muted)
                Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    LayoutChoice(prefs, HubLayout.Auto, R.string.hub_layout_auto, onChange)
                    LayoutChoice(prefs, HubLayout.Widgets, R.string.hub_layout_widgets, onChange)
                    LayoutChoice(prefs, HubLayout.Audio, R.string.hub_layout_audio, onChange)
                }
                ToggleRow(stringResource(R.string.hub_native_mic), prefs.microphone) { value -> onChange { it.copy(microphone = value) } }
                ToggleRow(stringResource(R.string.hub_native_camera), prefs.camera) { value -> onChange { it.copy(camera = value) } }
                ToggleRow(stringResource(R.string.hub_native_location), prefs.location) { value -> onChange { it.copy(location = value) } }
                ToggleRow(stringResource(R.string.hub_server_page), prefs.serverPage) { value -> onChange { it.copy(serverPage = value) } }
                if (missingPermissions) {
                    Text(stringResource(R.string.hub_permissions_missing), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error)
                    TextButton(onClick = onRequestPermissions) { Text(stringResource(R.string.hub_permissions_ask)) }
                }
            }
        },
        confirmButton = { TextButton(onClick = onOpenApp) { Text(stringResource(R.string.hub_open_app)) } },
        dismissButton = { TextButton(onClick = onDismiss) { Text(stringResource(R.string.cancel)) } },
    )
}

@Composable
private fun LayoutChoice(prefs: HubPrefs, layout: HubLayout, label: Int, onChange: ((HubPrefs) -> HubPrefs) -> Unit) {
    FilterChip(
        selected = prefs.layout == layout,
        onClick = { onChange { it.copy(layout = layout) } },
        label = { Text(stringResource(label), style = MaterialTheme.typography.labelSmall) },
        modifier = Modifier,
    )
}
