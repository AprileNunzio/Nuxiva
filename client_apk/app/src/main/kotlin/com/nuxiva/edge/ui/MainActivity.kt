package com.nuxiva.edge.ui

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.core.content.ContextCompat

class MainActivity : ComponentActivity() {
    private val model: AppViewModel by viewModels()
    private val notifications = registerForActivityResult(ActivityResultContracts.RequestPermission()) { }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        handle(intent, fresh = savedInstanceState == null)
        if (savedInstanceState == null && intent?.action == Intent.ACTION_MAIN && model.shouldOpenHub()) {
            com.nuxiva.edge.hub.HubActivity.start(this)
        }
        setContent { NuxivaTheme { AppScaffold(model) } }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handle(intent, fresh = true)
    }

    override fun onStart() {
        super.onStart()
        askNotifications()
        model.ensureService()
    }

    private fun askNotifications() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED) return
        notifications.launch(Manifest.permission.POST_NOTIFICATIONS)
    }

    private fun handle(incoming: Intent?, fresh: Boolean) {
        val current = incoming ?: return
        if (!fresh || current.action != Intent.ACTION_VIEW) return
        val link = current.dataString ?: return
        model.offerEnrollment(link)
        current.data = null
    }
}
