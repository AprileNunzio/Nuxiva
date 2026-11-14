package com.nuxiva.edge.ui

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Share
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationRail
import androidx.compose.material3.NavigationRailItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.repeatOnLifecycle
import com.nuxiva.edge.R
import com.nuxiva.edge.node.RuntimeEvent
import kotlinx.coroutines.delay

enum class Tab(val label: Int, val icon: ImageVector) {
    Nodes(R.string.tab_nodes, Icons.Filled.Home),
    Device(R.string.tab_device, Icons.Filled.Info),
    Share(R.string.tab_share, Icons.Filled.Share),
    Add(R.string.tab_add, Icons.Filled.Add),
}

@Composable
fun AppScaffold(model: AppViewModel) {
    var tab by rememberSaveable { mutableStateOf(Tab.Nodes) }
    val enroll by model.enroll.collectAsState()
    val profiles by model.profiles.collectAsState()
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    val snackbar = remember { SnackbarHostState() }
    val identified = stringResource(R.string.identify_message)

    LaunchedEffect(lifecycle) {
        lifecycle.repeatOnLifecycle(Lifecycle.State.STARTED) {
            while (true) {
                model.refresh()
                delay(REFRESH_MILLIS)
            }
        }
    }
    LaunchedEffect(enroll) {
        if (enroll !is EnrollUi.Idle) tab = Tab.Add
    }
    LaunchedEffect(profiles.isEmpty()) {
        if (profiles.isEmpty() && enroll is EnrollUi.Idle) tab = Tab.Add
    }
    LaunchedEffect(Unit) {
        model.events.collect { event ->
            if (event is RuntimeEvent.Identify) snackbar.showSnackbar(identified)
        }
    }

    BoxWithConstraints(Modifier.fillMaxSize()) {
        val wide = maxWidth >= RAIL_BREAKPOINT
        Scaffold(
            containerColor = MaterialTheme.colorScheme.background,
            snackbarHost = { SnackbarHost(snackbar) },
            bottomBar = {
                if (!wide) {
                    NavigationBar {
                        Tab.entries.forEach { entry ->
                            NavigationBarItem(
                                selected = tab == entry,
                                onClick = { tab = entry },
                                icon = { Icon(entry.icon, contentDescription = null) },
                                label = { Text(stringResource(entry.label)) },
                            )
                        }
                    }
                }
            },
        ) { padding ->
            Row(Modifier.fillMaxSize().padding(padding)) {
                if (wide) {
                    NavigationRail {
                        Tab.entries.forEach { entry ->
                            NavigationRailItem(
                                selected = tab == entry,
                                onClick = { tab = entry },
                                icon = { Icon(entry.icon, contentDescription = null) },
                                label = { Text(stringResource(entry.label)) },
                            )
                        }
                    }
                }
                Box(Modifier.weight(1f).fillMaxHeight(), contentAlignment = Alignment.TopCenter) {
                    Box(Modifier.widthIn(max = MAX_CONTENT).fillMaxWidth()) {
                        when (tab) {
                            Tab.Nodes -> NodesScreen(model, onAdd = { tab = Tab.Add })
                            Tab.Device -> DeviceScreen(model)
                            Tab.Share -> ShareScreen(model)
                            Tab.Add -> EnrollScreen(model, onDone = { tab = Tab.Nodes })
                        }
                    }
                }
            }
        }
    }
}

private val RAIL_BREAKPOINT = 600.dp
private val MAX_CONTENT = 1200.dp
private const val REFRESH_MILLIS = 5000L
