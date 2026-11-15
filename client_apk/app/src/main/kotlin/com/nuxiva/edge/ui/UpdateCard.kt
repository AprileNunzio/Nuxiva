package com.nuxiva.edge.ui

import android.content.Intent
import android.net.Uri
import android.provider.Settings
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.nuxiva.edge.BuildConfig
import com.nuxiva.edge.R
import com.nuxiva.edge.update.ApkUpdater
import com.nuxiva.edge.update.InstallStart
import com.nuxiva.logic.update.UpdateStep

@Composable
fun UpdateCard(updater: ApkUpdater) {
    val context = LocalContext.current
    val tokens = LocalTokens.current
    val ui by updater.ui.collectAsState()
    var needsPermission by remember { mutableStateOf(false) }
    InfoCard(stringResource(R.string.update_title)) {
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(stringResource(R.string.update_current, BuildConfig.VERSION_NAME), style = MaterialTheme.typography.bodyMedium)
            val offer = ui.offer
            when (ui.step) {
                UpdateStep.Downloading -> Text(stringResource(R.string.update_downloading), color = tokens.accent)
                UpdateStep.Installing -> Text(stringResource(R.string.update_installing), color = tokens.accent)
                UpdateStep.AwaitingUser -> {
                    Text(stringResource(R.string.update_ready), style = MaterialTheme.typography.bodySmall, color = tokens.muted)
                    PrimaryAction(stringResource(R.string.update_install), onClick = {
                        when (updater.install()) {
                            InstallStart.NeedsPermission -> {
                                needsPermission = true
                                context.startActivity(
                                    Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:${context.packageName}")).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
                                )
                            }
                            else -> needsPermission = false
                        }
                    })
                    if (needsPermission) Text(stringResource(R.string.update_permission_hint), style = MaterialTheme.typography.bodySmall, color = tokens.warn)
                }
                UpdateStep.Failed -> {
                    Text(stringResource(R.string.update_failed, ui.errorCode.orEmpty()), color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
                    if (offer != null) PrimaryAction(stringResource(R.string.update_retry), onClick = { updater.download() })
                }
                else -> {
                    if (offer == null) {
                        Text(stringResource(R.string.update_none), color = tokens.muted, style = MaterialTheme.typography.bodySmall)
                    } else {
                        Text(stringResource(R.string.update_available, offer.version), color = tokens.accent)
                        PrimaryAction(stringResource(R.string.update_download), onClick = { updater.download() })
                    }
                }
            }
        }
    }
}
