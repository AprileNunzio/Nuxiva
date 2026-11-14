package com.nuxiva.edge.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.nuxiva.edge.R
import com.nuxiva.edge.node.LinkState
import com.nuxiva.edge.node.NodeProfile
import com.nuxiva.logic.net.PinnedTrust
import java.net.URI

@Composable
fun NodesScreen(model: AppViewModel, onAdd: () -> Unit) {
    val profiles by model.profiles.collectAsState()
    val links by model.links.collectAsState()
    val running by model.running.collectAsState()
    val failure by model.loadFailure.collectAsState()
    var pending by remember { mutableStateOf<NodeProfile?>(null) }
    val context = androidx.compose.ui.platform.LocalContext.current

    LazyVerticalGrid(
        columns = GridCells.Adaptive(340.dp),
        contentPadding = PaddingValues(16.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        if (profiles.any { it.enabled }) {
            fullSpan("hub") {
                InfoCard(stringResource(R.string.hub_title)) {
                    Text(stringResource(R.string.hub_body), style = MaterialTheme.typography.bodyMedium)
                    Button(onClick = { com.nuxiva.edge.hub.HubActivity.start(context) }) { Text(stringResource(R.string.hub_open)) }
                }
            }
        }
        fullSpan("service") {
            InfoCard(stringResource(R.string.service_title)) {
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        stringResource(if (running) R.string.service_on else R.string.service_off),
                        modifier = Modifier.weight(1f),
                        style = MaterialTheme.typography.bodyLarge,
                    )
                    Switch(checked = running, onCheckedChange = model::setService, enabled = profiles.any { it.enabled })
                }
                Text(stringResource(R.string.service_hint), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.secondary)
            }
        }
        if (failure != null) {
            fullSpan("failure") {
                InfoCard(stringResource(R.string.vault_failure_title)) {
                    Text(stringResource(R.string.vault_failure_body), color = MaterialTheme.colorScheme.error)
                }
            }
        }
        if (profiles.isEmpty()) {
            fullSpan("empty") {
                InfoCard(stringResource(R.string.nodes_empty_title)) {
                    Text(stringResource(R.string.nodes_empty_body))
                    Button(onClick = onAdd) { Text(stringResource(R.string.nodes_add)) }
                }
            }
        }
        items(profiles, key = { it.nodeId }) { profile ->
            ProfileCard(profile, links[profile.nodeId], model, onRemove = { pending = profile })
        }
    }

    pending?.let { profile ->
        AlertDialog(
            onDismissRequest = { pending = null },
            title = { Text(stringResource(R.string.remove_title, profile.name)) },
            text = { Text(stringResource(R.string.remove_body)) },
            confirmButton = {
                TextButton(onClick = { model.remove(profile.nodeId); pending = null }) { Text(stringResource(R.string.remove_confirm)) }
            },
            dismissButton = { TextButton(onClick = { pending = null }) { Text(stringResource(R.string.cancel)) } },
        )
    }
}

@Composable
private fun ProfileCard(profile: NodeProfile, state: LinkState?, model: AppViewModel, onRemove: () -> Unit) {
    val host = runCatching { URI(profile.server).host }.getOrNull().orEmpty()
    val color = when (state) {
        is LinkState.Online -> MaterialTheme.colorScheme.primary
        is LinkState.Revoked, is LinkState.SecurityAlert -> MaterialTheme.colorScheme.error
        else -> MaterialTheme.colorScheme.secondary
    }
    InfoCard(profile.name) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(stringResource(linkLabel(state)), color = color, style = MaterialTheme.typography.titleSmall)
                if (state is LinkState.Offline) {
                    Text(state.code, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.secondary)
                }
            }
            Switch(checked = profile.enabled, onCheckedChange = { model.setEnabled(profile.nodeId, it) })
            IconButton(onClick = onRemove) {
                Icon(Icons.Filled.Delete, contentDescription = stringResource(R.string.remove_confirm))
            }
        }
        KeyValue(stringResource(R.string.field_server), host)
        KeyValue(stringResource(R.string.field_node_id), profile.nodeId)
        KeyValue(stringResource(R.string.field_fingerprint), PinnedTrust.short(profile.pin))
        if (state is LinkState.Revoked) {
            Text(stringResource(R.string.revoked_hint), color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(top = 4.dp))
        }
        if (state is LinkState.SecurityAlert) {
            Text(stringResource(R.string.security_hint), color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(top = 4.dp))
        }
    }
}
