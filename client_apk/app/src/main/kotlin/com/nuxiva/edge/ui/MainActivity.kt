package com.nuxiva.edge.ui

import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.core.content.ContextCompat

class MainActivity : ComponentActivity() {
    private val model: AppViewModel by viewModels()
    private val firstRun = registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { explainThenLaunch() }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        handle(intent, fresh = savedInstanceState == null)
        if (savedInstanceState == null && intent?.action == Intent.ACTION_MAIN) startup()
        setContent { NuxivaTheme { AppScaffold(model) } }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handle(intent, fresh = true)
    }

    override fun onStart() {
        super.onStart()
        model.ensureService()
    }

    private fun startup() {
        val hub = model.hubPrefs.value
        val missing = PermissionGuide.requestable().filter { ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED }
        if (!hub.permissionsAsked && missing.isNotEmpty()) {
            model.updateHub { it.copy(permissionsAsked = true) }
            firstRun.launch(missing.toTypedArray())
            return
        }
        explainThenLaunch()
    }

    private fun explainThenLaunch() {
        if (!PermissionGuide.show(this) { launchHub() }) launchHub()
    }

    private fun launchHub() {
        model.ensureService()
        if (!model.shouldOpenHub()) return
        com.nuxiva.edge.hub.HubActivity.start(this)
        finish()
    }

    private fun handle(incoming: Intent?, fresh: Boolean) {
        val current = incoming ?: return
        if (!fresh || current.action != Intent.ACTION_VIEW) return
        val link = current.dataString ?: return
        model.offerEnrollment(link)
        current.data = null
    }
}
