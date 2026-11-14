package com.nuxiva.edge.ui

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Build
import androidx.compose.material.icons.outlined.Home
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material.icons.outlined.Share
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.NavigationRail
import androidx.compose.material3.NavigationRailItem
import androidx.compose.material3.NavigationRailItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
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
    Home(R.string.tab_home, Icons.Outlined.Home),
    Network(R.string.tab_nodes, Icons.Outlined.Share),
    Resources(R.string.tab_share, Icons.Outlined.Build),
    Sensors(R.string.tab_device, Icons.Outlined.Info),
    Settings(R.string.tab_settings, Icons.Outlined.Settings),
}

@Composable
fun AppScaffold(model: AppViewModel) {
    var tab by rememberSaveable { mutableStateOf(Tab.Home) }
    var pairing by rememberSaveable { mutableStateOf(false) }
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
        if (enroll !is EnrollUi.Idle) pairing = true
    }
    LaunchedEffect(profiles.isEmpty()) {
        if (profiles.isEmpty() && enroll is EnrollUi.Idle) pairing = true
    }
    LaunchedEffect(Unit) {
        model.events.collect { event ->
            if (event is RuntimeEvent.Identify) snackbar.showSnackbar(identified)
        }
    }

    BoxWithConstraints(Modifier.fillMaxSize()) {
        val wide = maxWidth >= RAIL_BREAKPOINT
        val itemColors = NavigationBarItemDefaults.colors(
            selectedIconColor = LocalTokens.current.accent,
            selectedTextColor = LocalTokens.current.accent,
            indicatorColor = LocalTokens.current.accentSoft,
            unselectedIconColor = LocalTokens.current.muted,
            unselectedTextColor = LocalTokens.current.muted,
        )
        val railColors = NavigationRailItemDefaults.colors(
            selectedIconColor = LocalTokens.current.accent,
            selectedTextColor = LocalTokens.current.accent,
            indicatorColor = LocalTokens.current.accentSoft,
            unselectedIconColor = LocalTokens.current.muted,
            unselectedTextColor = LocalTokens.current.muted,
        )
        Scaffold(
            containerColor = MaterialTheme.colorScheme.background,
            snackbarHost = { SnackbarHost(snackbar) },
            bottomBar = {
                if (!wide && !pairing) {
                    NavigationBar(containerColor = MaterialTheme.colorScheme.background, tonalElevation = 0.dp) {
                        Tab.entries.forEach { entry ->
                            NavigationBarItem(
                                selected = tab == entry,
                                onClick = { tab = entry },
                                icon = { Icon(entry.icon, contentDescription = null) },
                                label = { Text(stringResource(entry.label), style = MaterialTheme.typography.labelSmall) },
                                colors = itemColors,
                            )
                        }
                    }
                }
            },
        ) { padding ->
            Row(Modifier.fillMaxSize().padding(padding)) {
                if (wide && !pairing) {
                    NavigationRail(containerColor = MaterialTheme.colorScheme.background) {
                        Tab.entries.forEach { entry ->
                            NavigationRailItem(
                                selected = tab == entry,
                                onClick = { tab = entry },
                                icon = { Icon(entry.icon, contentDescription = null) },
                                label = { Text(stringResource(entry.label), style = MaterialTheme.typography.labelSmall) },
                                colors = railColors,
                            )
                        }
                    }
                }
                Box(Modifier.weight(1f).fillMaxHeight(), contentAlignment = Alignment.TopCenter) {
                    Box(Modifier.widthIn(max = MAX_CONTENT).fillMaxSize()) {
                        if (pairing) {
                            Column {
                                if (profiles.isNotEmpty()) {
                                    Box(Modifier.padding(start = 16.dp, top = 12.dp)) {
                                        PrimaryAction(stringResource(R.string.cancel), { model.resetEnrollment(); pairing = false })
                                    }
                                }
                                EnrollScreen(model, onDone = { pairing = false; tab = Tab.Home })
                            }
                        } else {
                            when (tab) {
                                Tab.Home -> HomeScreen(model, onPair = { pairing = true })
                                Tab.Network -> NodesScreen(model, onAdd = { pairing = true })
                                Tab.Resources -> ShareScreen(model)
                                Tab.Sensors -> DeviceScreen(model)
                                Tab.Settings -> SettingsScreen(model, onPair = { pairing = true })
                            }
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
