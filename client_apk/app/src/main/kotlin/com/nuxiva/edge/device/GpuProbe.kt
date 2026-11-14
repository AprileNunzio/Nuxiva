package com.nuxiva.edge.device

import android.opengl.EGL14
import android.opengl.EGLConfig
import android.opengl.EGLContext
import android.opengl.EGLSurface
import android.opengl.GLES20
import android.util.Log

object GpuProbe {
    private const val TAG = "NuxivaGpu"

    @Volatile
    private var cached: String? = null

    fun renderer(): String {
        cached?.let { return it }
        val value = query()
        cached = value
        return value
    }

    private fun query(): String {
        val display = EGL14.eglGetDisplay(EGL14.EGL_DEFAULT_DISPLAY)
        if (display == EGL14.EGL_NO_DISPLAY) return ""
        val version = IntArray(2)
        if (!EGL14.eglInitialize(display, version, 0, version, 1)) return ""
        var surface: EGLSurface = EGL14.EGL_NO_SURFACE
        var context: EGLContext = EGL14.EGL_NO_CONTEXT
        try {
            val configs = arrayOfNulls<EGLConfig>(1)
            val count = IntArray(1)
            val attributes = intArrayOf(
                EGL14.EGL_RENDERABLE_TYPE, EGL14.EGL_OPENGL_ES2_BIT,
                EGL14.EGL_SURFACE_TYPE, EGL14.EGL_PBUFFER_BIT,
                EGL14.EGL_NONE,
            )
            if (!EGL14.eglChooseConfig(display, attributes, 0, configs, 0, 1, count, 0) || count[0] == 0) return ""
            val config = configs[0] ?: return ""
            surface = EGL14.eglCreatePbufferSurface(display, config, intArrayOf(EGL14.EGL_WIDTH, 1, EGL14.EGL_HEIGHT, 1, EGL14.EGL_NONE), 0)
            context = EGL14.eglCreateContext(display, config, EGL14.EGL_NO_CONTEXT, intArrayOf(EGL14.EGL_CONTEXT_CLIENT_VERSION, 2, EGL14.EGL_NONE), 0)
            if (surface == EGL14.EGL_NO_SURFACE || context == EGL14.EGL_NO_CONTEXT) return ""
            if (!EGL14.eglMakeCurrent(display, surface, surface, context)) return ""
            return GLES20.glGetString(GLES20.GL_RENDERER).orEmpty()
        } catch (error: RuntimeException) {
            Log.w(TAG, "GPU probe failed", error)
            return ""
        } finally {
            EGL14.eglMakeCurrent(display, EGL14.EGL_NO_SURFACE, EGL14.EGL_NO_SURFACE, EGL14.EGL_NO_CONTEXT)
            if (surface != EGL14.EGL_NO_SURFACE) EGL14.eglDestroySurface(display, surface)
            if (context != EGL14.EGL_NO_CONTEXT) EGL14.eglDestroyContext(display, context)
            EGL14.eglTerminate(display)
        }
    }
}
