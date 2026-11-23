package com.nuxiva.edge.node

import android.content.Context
import android.net.wifi.WifiManager

class MulticastGuard(context: Context) {
    private val lock: WifiManager.MulticastLock? =
        (context.applicationContext.getSystemService(Context.WIFI_SERVICE) as? WifiManager)
            ?.createMulticastLock("nuxiva-peer")
            ?.apply { setReferenceCounted(true) }

    fun acquire() {
        lock?.takeIf { !it.isHeld }?.acquire()
    }

    fun release() {
        lock?.takeIf { it.isHeld }?.release()
    }
}
