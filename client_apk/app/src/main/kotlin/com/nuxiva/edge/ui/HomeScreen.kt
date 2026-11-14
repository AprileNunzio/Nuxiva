package com.nuxiva.edge.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.nuxiva.edge.R
import com.nuxiva.edge.hub.HubActivity
import com.nuxiva.edge.node.LinkState
import com.nuxiva.logic.compute.ShareDecision
import com.nuxiva.logic.compute.SharePolicy

@Composable
fun HomeScreen(model: AppViewModel, onPair: () -> Unit) {
    val context = LocalContext.current
    val tokens = LocalTokens.current
    val profiles by model.profiles.collectAsState()
    val links by model.links.collectAsState()
    val power by model.powerSnapshot.collectAsState()
    val facts by model.deviceFacts.collectAsState()
    val settings by model.share.collectAsState()
    val ollama by model.ollamaState.collectAsState()
    val enabled = profiles.filter { it.enabled }
    val online = enabled.count { links[it.nodeId] is LinkState.Online }
    val tone = when {
        enabled.isEmpty() -> tokens.muted
        online == enabled.size -> tokens.ok
        online > 0 -> tokens.warn
        else -> MaterialTheme.colorScheme.error
    }
    val state = stringResource(
        when {
            enabled.isEmpty() -> R.string.home_state_empty
            online == enabled.size -> R.string.home_state_online
            online > 0 -> R.string.home_state_partial
            else -> R.string.home_state_offline
        },
    )
    val decision = power?.let { SharePolicy.decide(settings, it) }
    val sharing = when {
        decision is ShareDecision.Denied -> stringResource(denyLabel(decision.reason))
        decision == ShareDecision.Allowed && !ollama.available -> stringResource(R.string.share_waiting_engine)
        decision == ShareDecision.Allowed -> stringResource(R.string.share_active)
        else -> stringResource(R.string.device_loading)
    }
    LazyVerticalGrid(
        columns = GridCells.Adaptive(220.dp),
        contentPadding = PaddingValues(16.dp),
        horizontalArrangement = Arrangement.spacedBy(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        fullSpan("orb") { Orb(tone, state, stringResource(R.string.home_servers, online, enabled.size)) }
        fullSpan("actions") {
            Column(Modifier.fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(8.dp)) {
                if (enabled.isEmpty()) {
                    PrimaryAction(stringResource(R.string.nodes_add), onPair)
                } else {
                    PrimaryAction(stringResource(R.string.hub_open), { HubActivity.start(context) })
                    Text(stringResource(R.string.hub_body), style = MaterialTheme.typography.bodySmall, color = tokens.muted, textAlign = TextAlign.Center)
                }
            }
        }
        power?.let { snapshot ->
            item("battery") {
                Stat(stringResource(R.string.field_battery), "${snapshot.batteryPercent}%", fraction = snapshot.batteryPercent / 100f, marker = settings.minBatteryPercent / 100f)
            }
            item("temperature") {
                Stat(stringResource(R.string.field_temperature), snapshot.batteryTempDeciC?.let { "%.1f °C".format(it / 10.0) } ?: "-")
            }
            item("network") {
                Stat(stringResource(R.string.field_network), stringResource(if (snapshot.unmetered) R.string.network_unmetered else R.string.network_metered))
            }
        }
        facts?.let { current ->
            item("ram") { Stat(stringResource(R.string.field_ram), "%.1f GB".format(current.ramMb / 1024.0)) }
            item("cpu") { Stat(stringResource(R.string.field_cpu), stringResource(R.string.value_cores, current.cores)) }
            item("gpu") { Stat(stringResource(R.string.field_gpu), current.gpu.ifEmpty { "-" }) }
        }
        fullSpan("sharing") {
            InfoCard(stringResource(R.string.share_title)) {
                Text(sharing, style = MaterialTheme.typography.titleSmall, color = tokens.accent)
            }
        }
    }
}

@Composable
private fun Orb(color: Color, label: String, detail: String) {
    val tokens = LocalTokens.current
    val breathe by pulse(0.9f, 1f, 2600)
    Box(Modifier.fillMaxWidth().height(250.dp), contentAlignment = Alignment.Center) {
        Canvas(Modifier.size(230.dp)) {
            val radius = size.minDimension / 2f
            drawCircle(
                brush = Brush.radialGradient(listOf(color.copy(alpha = 0.3f), Color.Transparent), center = center, radius = radius),
                radius = radius * breathe,
            )
            drawCircle(color.copy(alpha = 0.55f), radius = radius * 0.62f, style = Stroke(1.5.dp.toPx()))
            drawCircle(brush = tokens.ink, radius = radius * 0.46f, style = Stroke(3.dp.toPx()))
        }
        Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(label, style = MaterialTheme.typography.titleLarge, textAlign = TextAlign.Center, modifier = Modifier.widthIn(max = 140.dp))
            Text(detail.uppercase(), style = MaterialTheme.typography.labelSmall, color = tokens.muted)
        }
    }
}
