package com.nuxiva.edge.ui

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import com.nuxiva.edge.R
import java.net.URI

@Composable
fun EnrollScreen(model: AppViewModel, onDone: () -> Unit) {
    val state by model.enroll.collectAsState()
    Column(
        Modifier.verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        when (val current = state) {
            EnrollUi.Idle -> IdleForm(model)
            is EnrollUi.Review -> ReviewForm(model, current)
            EnrollUi.Working -> InfoCard(stringResource(R.string.enroll_working_title)) {
                CircularProgressIndicator()
                Text(stringResource(R.string.enroll_working_body))
            }
            is EnrollUi.Failed -> InfoCard(stringResource(R.string.enroll_failed_title)) {
                Text(stringResource(errorLabel(current.code)), color = MaterialTheme.colorScheme.error)
                Button(onClick = model::resetEnrollment) { Text(stringResource(R.string.enroll_try_again)) }
            }
            is EnrollUi.Done -> InfoCard(stringResource(R.string.enroll_done_title)) {
                Text(stringResource(R.string.enroll_done_body, current.nodeId))
                Button(onClick = { model.resetEnrollment(); onDone() }) { Text(stringResource(R.string.enroll_go_nodes)) }
            }
        }
    }
}

@Composable
private fun IdleForm(model: AppViewModel) {
    val context = LocalContext.current
    var scanning by rememberSaveable { mutableStateOf(false) }
    var pasted by rememberSaveable { mutableStateOf("") }
    val permission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted -> scanning = granted }

    InfoCard(stringResource(R.string.enroll_title)) {
        Text(stringResource(R.string.enroll_intro))
        Text(stringResource(R.string.enroll_steps), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.secondary)
        if (scanning) {
            QrScanner(
                onResult = { value -> scanning = false; model.offerEnrollment(value) },
                modifier = Modifier.fillMaxWidth().aspectRatio(1f).clip(RoundedCornerShape(16.dp)),
            )
            OutlinedButton(onClick = { scanning = false }) { Text(stringResource(R.string.cancel)) }
        } else {
            Button(onClick = {
                val granted = ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED
                if (granted) scanning = true else permission.launch(Manifest.permission.CAMERA)
            }) { Text(stringResource(R.string.enroll_scan)) }
        }
    }
    InfoCard(stringResource(R.string.enroll_paste_title)) {
        OutlinedTextField(
            value = pasted,
            onValueChange = { pasted = it.take(PASTE_LIMIT) },
            label = { Text(stringResource(R.string.enroll_paste_label)) },
            modifier = Modifier.fillMaxWidth(),
            minLines = 3,
            keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(keyboardType = KeyboardType.Uri),
        )
        Button(onClick = { model.offerEnrollment(pasted); pasted = "" }, enabled = pasted.isNotBlank()) {
            Text(stringResource(R.string.enroll_continue))
        }
    }
}

@Composable
private fun ReviewForm(model: AppViewModel, review: EnrollUi.Review) {
    var name by rememberSaveable { mutableStateOf("") }
    LaunchedEffect(Unit) { if (name.isEmpty()) name = model.defaultNodeName() }
    val host = remember(review) { runCatching { URI(review.payload.server).authority }.getOrNull().orEmpty() }
    InfoCard(stringResource(R.string.enroll_review_title)) {
        Text(stringResource(R.string.enroll_review_body))
        KeyValue(stringResource(R.string.field_server), host)
        KeyValue(stringResource(R.string.field_fingerprint), review.pinShort)
        OutlinedTextField(
            value = name,
            onValueChange = { name = it.take(NAME_LIMIT) },
            label = { Text(stringResource(R.string.enroll_name_label)) },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = { model.confirmEnrollment(name) }, enabled = name.isNotBlank()) { Text(stringResource(R.string.enroll_confirm)) }
            OutlinedButton(onClick = model::resetEnrollment) { Text(stringResource(R.string.cancel)) }
        }
    }
}

private const val PASTE_LIMIT = 8192
private const val NAME_LIMIT = 60
