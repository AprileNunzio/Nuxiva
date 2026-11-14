package com.nuxiva.edge.service

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.nuxiva.edge.core.graph

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED) return
        if (context.graph.profiles.profiles.value.none { it.enabled }) return
        if (ServiceSwitch.userStopped(context)) return
        NodeService.start(context)
    }
}

object ServiceSwitch {
    private const val FILE = "nuxiva_service"
    private const val STOPPED = "user_stopped"

    fun userStopped(context: Context): Boolean =
        context.getSharedPreferences(FILE, Context.MODE_PRIVATE).getBoolean(STOPPED, false)

    fun setUserStopped(context: Context, stopped: Boolean) {
        context.getSharedPreferences(FILE, Context.MODE_PRIVATE).edit().putBoolean(STOPPED, stopped).apply()
    }
}
