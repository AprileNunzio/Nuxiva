package com.nuxiva.edge.device

import android.content.Context
import android.hardware.display.DisplayManager
import android.os.Handler
import android.os.Looper
import android.util.DisplayMetrics
import android.view.Display
import com.nuxiva.logic.device.Orientation
import com.nuxiva.logic.device.OrientationState
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

class OrientationMonitor(context: Context) {
    private val displays = context.getSystemService(DisplayManager::class.java)
    private val state = MutableStateFlow(read(null))
    private var users = 0

    val current: StateFlow<OrientationState> = state.asStateFlow()

    private val listener = object : DisplayManager.DisplayListener {
        override fun onDisplayAdded(displayId: Int) = Unit
        override fun onDisplayRemoved(displayId: Int) = Unit
        override fun onDisplayChanged(displayId: Int) {
            if (displayId == Display.DEFAULT_DISPLAY) state.value = read(state.value)
        }
    }

    @Synchronized
    fun start() {
        users += 1
        if (users != 1) return
        displays.registerDisplayListener(listener, Handler(Looper.getMainLooper()))
        state.value = read(state.value)
    }

    @Synchronized
    fun stop() {
        if (users == 0) return
        users -= 1
        if (users == 0) displays.unregisterDisplayListener(listener)
    }

    fun displayMetrics(): DisplayMetrics {
        val metrics = DisplayMetrics()
        @Suppress("DEPRECATION")
        displays.getDisplay(Display.DEFAULT_DISPLAY)?.getRealMetrics(metrics)
        return metrics
    }

    fun refreshRate(): Int = displays.getDisplay(Display.DEFAULT_DISPLAY)?.refreshRate?.let { Math.round(it) } ?: 0

    private fun read(previous: OrientationState?): OrientationState {
        val display = displays.getDisplay(Display.DEFAULT_DISPLAY)
        val metrics = displayMetrics()
        return Orientation.next(previous, display?.rotation ?: 0, metrics.widthPixels, metrics.heightPixels)
    }
}
