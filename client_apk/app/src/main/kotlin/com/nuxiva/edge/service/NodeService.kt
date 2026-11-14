package com.nuxiva.edge.service

import android.app.Notification
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import com.nuxiva.edge.R
import com.nuxiva.edge.core.NuxivaApplication
import com.nuxiva.edge.core.graph
import com.nuxiva.edge.node.LinkState
import com.nuxiva.edge.ui.MainActivity
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.launch

class NodeService : Service() {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)

    override fun onCreate() {
        super.onCreate()
        val appGraph = graph
        startInForeground(buildNotification(0, 0, false))
        appGraph.runtime.start()
        scope.launch {
            combine(appGraph.runtime.links, appGraph.profiles.profiles, appGraph.shareSettings.settings) { links, profiles, share ->
                val enabled = profiles.filter { it.enabled }
                val online = enabled.count { links[it.nodeId] is LinkState.Online }
                Triple(online, enabled.size, share.consent && !share.killSwitch)
            }.collect { (online, total, sharing) ->
                getSystemService(android.app.NotificationManager::class.java)
                    .notify(NOTIFICATION_ID, buildNotification(online, total, sharing))
            }
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> {
                ServiceSwitch.setUserStopped(this, true)
                graph.runtime.stop()
                stopForeground(STOP_FOREGROUND_REMOVE)
                stopSelf()
                return START_NOT_STICKY
            }
            ACTION_KILL_SHARING -> graph.shareSettings.update { it.copy(killSwitch = true) }
        }
        return START_STICKY
    }

    override fun onDestroy() {
        scope.cancel()
        graph.runtime.stop()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun startInForeground(notification: Notification) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE)
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }
    }

    private fun buildNotification(online: Int, total: Int, sharing: Boolean): Notification {
        val open = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE)
        val builder = NotificationCompat.Builder(this, NuxivaApplication.NODE_CHANNEL_ID)
            .setContentTitle(getString(R.string.notification_node_title))
            .setContentText(getString(R.string.notification_node_text, online, total))
            .setSmallIcon(R.drawable.ic_stat_node)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .setContentIntent(open)
            .addAction(0, getString(R.string.notification_action_stop), servicePendingIntent(ACTION_STOP, 1))
        if (sharing) {
            builder.addAction(0, getString(R.string.notification_action_kill), servicePendingIntent(ACTION_KILL_SHARING, 2))
        }
        return builder.build()
    }

    private fun servicePendingIntent(action: String, code: Int): PendingIntent =
        PendingIntent.getService(this, code, Intent(this, NodeService::class.java).setAction(action), PendingIntent.FLAG_IMMUTABLE)

    companion object {
        const val NOTIFICATION_ID = 2001
        const val ACTION_STOP = "com.nuxiva.edge.action.STOP"
        const val ACTION_KILL_SHARING = "com.nuxiva.edge.action.KILL_SHARING"

        fun start(context: Context) {
            ServiceSwitch.setUserStopped(context, false)
            ContextCompat.startForegroundService(context, Intent(context, NodeService::class.java))
        }

        fun stop(context: Context) {
            context.startService(Intent(context, NodeService::class.java).setAction(ACTION_STOP))
        }
    }
}
