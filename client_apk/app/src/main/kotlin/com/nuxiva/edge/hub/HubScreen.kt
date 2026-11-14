package com.nuxiva.edge.hub

import android.webkit.WebView
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import com.nuxiva.edge.R

@Composable
fun HubScreen(
    ui: HubUi,
    view: WebView?,
    media: HubMedia,
    menu: Boolean,
    settings: HubSettings,
    onMenu: (Boolean) -> Unit,
    onReload: () -> Unit,
    onClose: () -> Unit,
) {
    Box(Modifier.fillMaxSize().background(Color.Black)) {
        view?.let { AndroidView(factory = { it }, modifier = Modifier.fillMaxSize()) }
        if (ui !is HubUi.Showing) StatusLayer(ui, onReload, onClose)
        IconButton(onClick = { onMenu(true) }, modifier = Modifier.statusBarsPadding().align(Alignment.TopStart).alpha(MENU_ALPHA)) {
            Icon(Icons.Filled.Menu, contentDescription = stringResource(R.string.hub_menu_title), tint = Color.White)
        }
        Row(
            Modifier.statusBarsPadding().align(Alignment.TopEnd).padding(12.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            if (media.audio) Indicator(stringResource(R.string.hub_mic_on))
            if (media.video) Indicator(stringResource(R.string.hub_camera_on))
        }
    }
    if (menu) MenuDialog(settings, onDismiss = { onMenu(false) }, onReload = onReload, onClose = onClose)
}

@Composable
private fun Indicator(label: String) {
    Text(
        label,
        color = Color.White,
        style = MaterialTheme.typography.labelMedium,
        modifier = Modifier.background(Color(0xCCB91C1C), MaterialTheme.shapes.small).padding(horizontal = 10.dp, vertical = 4.dp),
    )
}

@Composable
private fun StatusLayer(ui: HubUi, onReload: () -> Unit, onClose: () -> Unit) {
    Box(Modifier.fillMaxSize().background(Color(0xFF030712)), contentAlignment = Alignment.Center) {
        Column(Modifier.padding(32.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(16.dp)) {
            when (ui) {
                HubUi.Connecting, HubUi.Showing -> {
                    CircularProgressIndicator(color = MaterialTheme.colorScheme.primary)
                    Text(stringResource(R.string.hub_connecting), color = Color.White, textAlign = TextAlign.Center)
                }
                is HubUi.Failed -> {
                    Text(stringResource(R.string.hub_failed_title), color = Color.White, style = MaterialTheme.typography.titleLarge)
                    Text(stringResource(R.string.hub_failed_body, ui.code), color = Color(0xFF94A3B8), textAlign = TextAlign.Center)
                    TextButton(onClick = onReload) { Text(stringResource(R.string.hub_menu_reload)) }
                }
                HubUi.NoServer -> {
                    Text(stringResource(R.string.hub_no_server), color = Color.White, textAlign = TextAlign.Center)
                    TextButton(onClick = onClose) { Text(stringResource(R.string.hub_menu_close)) }
                }
            }
        }
    }
}

@Composable
private fun MenuDialog(settings: HubSettings, onDismiss: () -> Unit, onReload: () -> Unit, onClose: () -> Unit) {
    val prefs by settings.settings.collectAsState()
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.hub_menu_title)) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                ToggleLine(stringResource(R.string.hub_mic), prefs.microphone) { value -> settings.update { it.copy(microphone = value) } }
                ToggleLine(stringResource(R.string.hub_camera), prefs.camera) { value -> settings.update { it.copy(camera = value) } }
                Text(stringResource(R.string.hub_privacy_hint), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.secondary)
            }
        },
        confirmButton = { TextButton(onClick = onReload) { Text(stringResource(R.string.hub_menu_reload)) } },
        dismissButton = {
            Row {
                TextButton(onClick = onClose) { Text(stringResource(R.string.hub_menu_close)) }
                TextButton(onClick = onDismiss) { Text(stringResource(R.string.cancel)) }
            }
        },
    )
}

@Composable
private fun ToggleLine(label: String, checked: Boolean, onChange: (Boolean) -> Unit) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Text(label, modifier = Modifier.weight(1f))
        Switch(checked = checked, onCheckedChange = onChange)
    }
}

private const val MENU_ALPHA = 0.35f
