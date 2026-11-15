package com.nuxiva.edge.hub

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.horizontalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.nuxiva.edge.R
import com.nuxiva.edge.core.AppGraph
import com.nuxiva.edge.ui.LocalTokens
import com.nuxiva.edge.ui.Stat
import com.nuxiva.edge.ui.fullSpan
import java.time.format.DateTimeFormatter
import java.time.format.FormatStyle
import kotlin.math.min

private val WIDE_BREAKPOINT = 600.dp

@Composable
fun MobileHubScreen(graph: AppGraph, prefs: HubPrefs, onMenu: () -> Unit) {
    val tokens = LocalTokens.current
    val vitals by rememberVitals(graph)
    val clock by rememberClock()
    val reading by graph.audio.reading.collectAsState()
    val listening = prefs.microphone && reading != null
    val tone = when {
        vitals.total == 0 -> tokens.muted
        vitals.online == vitals.total -> tokens.ok
        vitals.online > 0 -> tokens.warn
        else -> MaterialTheme.colorScheme.error
    }
    val title = clock.format(DateTimeFormatter.ofLocalizedTime(FormatStyle.SHORT))
    val detail = stringResource(if (listening) R.string.hub_core_listening else R.string.hub_core_idle)
    val date = clock.format(DateTimeFormatter.ofLocalizedDate(FormatStyle.FULL))
    val link = stringResource(R.string.home_servers, vitals.online, vitals.total)
    BoxWithConstraints(
        Modifier
            .fillMaxSize()
            .background(Brush.verticalGradient(listOf(Color(0xFF050B16), Color(0xFF0B1220))))
            .statusBarsPadding()
            .navigationBarsPadding(),
    ) {
        val wide = maxWidth >= WIDE_BREAKPOINT
        val audioOnly = when (prefs.layout) {
            HubLayout.Audio -> true
            HubLayout.Widgets -> false
            HubLayout.Auto -> !wide
        }
        if (audioOnly) {
            Column(
                Modifier.fillMaxSize().padding(horizontal = 16.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center,
            ) {
                CoreOrb(tone, reading?.level ?: 0f, min(maxWidth.value * 0.82f, maxHeight.value * 0.5f).dp, title, detail)
                Text(date, style = MaterialTheme.typography.bodyMedium, color = tokens.muted, textAlign = TextAlign.Center, modifier = Modifier.padding(top = 20.dp))
                Row(
                    Modifier.padding(top = 20.dp).horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(20.dp),
                ) {
                    Chip(stringResource(R.string.field_hub_link), link)
                    vitals.battery?.let { Chip(stringResource(R.string.field_battery), "$it%") }
                    Chip(stringResource(R.string.field_network), stringResource(if (vitals.unmetered) R.string.network_unmetered else R.string.network_metered))
                }
            }
        } else {
            LazyVerticalGrid(
                columns = GridCells.Adaptive(190.dp),
                contentPadding = PaddingValues(start = 20.dp, end = 20.dp, top = 56.dp, bottom = 24.dp),
                horizontalArrangement = Arrangement.spacedBy(20.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                fullSpan("core") {
                    Column(Modifier.fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally) {
                        CoreOrb(tone, reading?.level ?: 0f, min(maxWidth.value * 0.5f, 260f).dp, title, detail)
                        Text(date, style = MaterialTheme.typography.bodyMedium, color = tokens.muted, modifier = Modifier.padding(top = 8.dp))
                    }
                }
                item("link") { Stat(stringResource(R.string.field_hub_link), link) }
                vitals.battery?.let { level ->
                    item("battery") {
                        Stat(
                            stringResource(R.string.field_battery),
                            if (vitals.charging) "$level% ${stringResource(R.string.hub_charging)}" else "$level%",
                            fraction = level / 100f,
                        )
                    }
                }
                vitals.ramPercent?.let { used ->
                    item("ram") { Stat(stringResource(R.string.field_ram), "$used%", fraction = used / 100f) }
                }
                item("network") {
                    Stat(stringResource(R.string.field_network), stringResource(if (vitals.unmetered) R.string.network_unmetered else R.string.network_metered))
                }
                item("sensors") { Stat(stringResource(R.string.hub_sensors_in_use), sensors(prefs)) }
            }
        }
        IconButton(onClick = onMenu, modifier = Modifier.align(Alignment.TopStart)) {
            Icon(Icons.Filled.Menu, contentDescription = stringResource(R.string.hub_menu_title), tint = Color.White)
        }
    }
}

@Composable
private fun Chip(label: String, value: String) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(label.uppercase(), style = MaterialTheme.typography.labelSmall, color = LocalTokens.current.muted)
        Text(value, style = MaterialTheme.typography.titleSmall)
    }
}

@Composable
private fun sensors(prefs: HubPrefs): String {
    val names = buildList {
        if (prefs.microphone) add(stringResource(R.string.hub_sensor_microphone))
        if (prefs.camera) add(stringResource(R.string.hub_sensor_camera))
        if (prefs.location) add(stringResource(R.string.hub_sensor_location))
    }
    return if (names.isEmpty()) stringResource(R.string.hub_sensor_none) else names.joinToString(" · ")
}
