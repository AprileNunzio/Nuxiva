package com.nuxiva.edge.hub

import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.State
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.produceState
import com.nuxiva.edge.core.AppGraph
import com.nuxiva.edge.node.LinkState
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import java.time.LocalDateTime

data class HubVitals(
    val online: Int = 0,
    val total: Int = 0,
    val battery: Int? = null,
    val charging: Boolean = false,
    val unmetered: Boolean = false,
    val ramPercent: Int? = null,
)

@Composable
fun rememberVitals(graph: AppGraph): State<HubVitals> {
    val links by graph.runtime.links.collectAsState()
    val profiles by graph.profiles.profiles.collectAsState()
    val state = remember { mutableStateOf(HubVitals()) }
    LaunchedEffect(links, profiles) {
        val enabled = profiles.filter { it.enabled }
        val online = enabled.count { links[it.nodeId] is LinkState.Online }
        while (true) {
            state.value = withContext(Dispatchers.IO) {
                val power = graph.power.snapshot()
                val total = graph.inspector.facts().ramMb
                val ram = if (total > 0) ((total - graph.inspector.availableRamMb()).coerceAtLeast(0) * 100 / total).toInt() else null
                HubVitals(online, enabled.size, power.batteryPercent, power.charging, power.unmetered, ram)
            }
            delay(VITALS_MILLIS)
        }
    }
    return state
}

@Composable
fun rememberClock(): State<LocalDateTime> = produceState(LocalDateTime.now()) {
    while (true) {
        value = LocalDateTime.now()
        delay(CLOCK_MILLIS - (System.currentTimeMillis() % CLOCK_MILLIS))
    }
}

private const val VITALS_MILLIS = 5_000L
private const val CLOCK_MILLIS = 30_000L
