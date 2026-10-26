package com.nuxiva.edge.core

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build

class NuxivaApplication : Application() {

    companion object {
        const val AUDIO_CHANNEL_ID = "nuxiva_continuous_audio_channel"
    }

    override fun onCreate() {
        super.onCreate()
        createNotificationChannels()
    }

    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val audioChannel = NotificationChannel(
                AUDIO_CHANNEL_ID,
                "Nuxiva Background Listener",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Mantiene il rilevatore di wake-word 'Nuxiva' permanentemente attivo su microfono locale."
                setShowBadge(false)
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager?.createNotificationChannel(audioChannel)
        }
    }
}
