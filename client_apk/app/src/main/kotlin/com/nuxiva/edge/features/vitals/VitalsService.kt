package com.nuxiva.edge.features.vitals

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

class VitalsService : Service() {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private lateinit var vault: VitalsVault
    private lateinit var uploader: VitalsUploader
    private var ble: BleVitalsMonitor? = null
    private var poller: Job? = null

    override fun onCreate() {
        super.onCreate()
        vault = VitalsVault(this)
        uploader = VitalsUploader(vault)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (!vault.linked()) {
            stopSelf()
            return START_NOT_STICKY
        }
        startForegroundCompat()
        ble = ble ?: BleVitalsMonitor(this, vault) { samples -> scope.launch { uploader.send(samples) } }
        runCatching { ble?.start() }
        if (poller?.isActive != true) {
            poller = scope.launch {
                val reader = HealthConnectReader(this@VitalsService)
                while (isActive) {
                    runCatching { uploader.send(reader.read()) }
                    delay(POLL_MS)
                }
            }
        }
        return START_STICKY
    }

    private fun startForegroundCompat() {
        val manager = getSystemService(NotificationManager::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            manager.createNotificationChannel(NotificationChannel(CHANNEL, "Nuxiva Vitals", NotificationManager.IMPORTANCE_LOW))
        }
        val notification: Notification = NotificationCompat.Builder(this, CHANNEL)
            .setContentTitle("Nuxiva")
            .setContentText("Parametri vitali collegati")
            .setSmallIcon(android.R.drawable.ic_menu_info_details)
            .setOngoing(true)
            .build()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_CONNECTED_DEVICE)
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }
    }

    override fun onDestroy() {
        ble?.stop()
        scope.cancel()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    companion object {
        private const val CHANNEL = "nuxiva_vitals_channel"
        private const val NOTIFICATION_ID = 4107
        private const val POLL_MS = 30_000L
    }
}
