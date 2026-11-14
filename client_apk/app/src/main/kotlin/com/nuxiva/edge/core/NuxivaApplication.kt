package com.nuxiva.edge.core

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import com.nuxiva.edge.R

class NuxivaApplication : Application() {

    lateinit var graph: AppGraph
        private set

    companion object {
        const val AUDIO_CHANNEL_ID = "nuxiva_continuous_audio_channel"
        const val NODE_CHANNEL_ID = "nuxiva_node_link_channel"
    }

    override fun onCreate() {
        super.onCreate()
        graph = AppGraph(this)
        createNotificationChannels()
    }

    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val manager = getSystemService(NotificationManager::class.java) ?: return
            manager.createNotificationChannel(
                NotificationChannel(AUDIO_CHANNEL_ID, getString(R.string.channel_audio_name), NotificationManager.IMPORTANCE_LOW).apply {
                    description = getString(R.string.channel_audio_description)
                    setShowBadge(false)
                },
            )
            manager.createNotificationChannel(
                NotificationChannel(NODE_CHANNEL_ID, getString(R.string.channel_node_name), NotificationManager.IMPORTANCE_LOW).apply {
                    description = getString(R.string.channel_node_description)
                    setShowBadge(false)
                },
            )
        }
    }
}

val android.content.Context.graph: AppGraph
    get() = (applicationContext as NuxivaApplication).graph
