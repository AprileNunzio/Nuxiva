package com.nuxiva.edge.hub

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.view.WindowManager
import android.webkit.WebView
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.core.content.ContextCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.nuxiva.edge.core.graph
import com.nuxiva.edge.node.NodeFailure
import com.nuxiva.edge.node.NodeProfile
import com.nuxiva.edge.ui.NuxivaTheme
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

sealed interface HubUi {
    data object Connecting : HubUi
    data object Showing : HubUi
    data class Failed(val code: String) : HubUi
    data object NoServer : HubUi
}

data class HubMedia(val audio: Boolean = false, val video: Boolean = false)

class HubActivity : ComponentActivity(), HubHost {
    private var ui by mutableStateOf<HubUi>(HubUi.Connecting)
    private var view by mutableStateOf<WebView?>(null)
    private var media by mutableStateOf(HubMedia())
    private var menu by mutableStateOf(false)
    private var loading = false
    private var pending: ((Boolean) -> Unit)? = null
    private var profile: NodeProfile? = null

    private val devicePermissions = registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { grants ->
        pending?.invoke(grants.isNotEmpty() && grants.values.all { it })
        pending = null
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        WindowCompat.setDecorFitsSystemWindows(window, false)
        setContent {
            NuxivaTheme {
                BackHandler { menu = true }
                HubScreen(
                    ui = ui,
                    view = view,
                    media = media,
                    menu = menu,
                    settings = application.graph.hub,
                    onMenu = { menu = it },
                    onReload = { menu = false; reload() },
                    onClose = { finish() },
                )
            }
        }
        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                while (isActive) {
                    if (view == null || ui is HubUi.Failed) connect()
                    delay(RETRY_MILLIS)
                }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        view?.onResume()
    }

    override fun onPause() {
        view?.onPause()
        super.onPause()
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (!hasFocus) return
        WindowInsetsControllerCompat(window, window.decorView).apply {
            systemBarsBehavior = WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
            hide(WindowInsetsCompat.Type.systemBars())
        }
    }

    override fun onDestroy() {
        view?.apply {
            stopLoading()
            destroy()
        }
        view = null
        super.onDestroy()
    }

    private fun pick(): NodeProfile? {
        val wanted = intent.getStringExtra(EXTRA_NODE)
        val all = application.graph.profiles.profiles.value.filter { it.enabled }
        return all.firstOrNull { it.nodeId == wanted } ?: all.firstOrNull()
    }

    private suspend fun connect() {
        if (loading) return
        loading = true
        try {
            val chosen = pick()
            if (chosen == null) {
                ui = HubUi.NoServer
                return
            }
            profile = chosen
            ui = HubUi.Connecting
            val url = HubLink.open(chosen)
            val current = view ?: hubWebView(this, chosen, this).also { view = it }
            current.loadUrl(url)
        } catch (error: CancellationException) {
            throw error
        } catch (error: NodeFailure) {
            ui = HubUi.Failed(error.code)
        } catch (error: Exception) {
            ui = HubUi.Failed("hub_error")
        } finally {
            loading = false
        }
    }

    private fun reload() {
        ui = HubUi.Connecting
        lifecycleScope.launch { connect() }
    }

    override fun microphoneAllowed(): Boolean = application.graph.hub.settings.value.microphone

    override fun cameraAllowed(): Boolean = application.graph.hub.settings.value.camera

    override fun ensureDevicePermissions(audio: Boolean, video: Boolean, result: (Boolean) -> Unit) {
        val needed = buildList {
            if (audio && !has(Manifest.permission.RECORD_AUDIO)) add(Manifest.permission.RECORD_AUDIO)
            if (video && !has(Manifest.permission.CAMERA)) add(Manifest.permission.CAMERA)
        }
        if (needed.isEmpty()) {
            result(true)
            return
        }
        pending?.invoke(false)
        pending = result
        devicePermissions.launch(needed.toTypedArray())
    }

    private fun has(permission: String): Boolean =
        ContextCompat.checkSelfPermission(this, permission) == PackageManager.PERMISSION_GRANTED

    override fun onMediaGranted(audio: Boolean, video: Boolean) {
        media = HubMedia(audio = media.audio || audio, video = media.video || video)
    }

    override fun onMediaReleased() {
        media = HubMedia()
    }

    override fun onLoaded() {
        ui = HubUi.Showing
    }

    override fun onFailure(code: String) {
        ui = HubUi.Failed(code)
    }

    companion object {
        const val EXTRA_NODE = "node"
        private const val RETRY_MILLIS = 10_000L

        fun start(context: Context, nodeId: String? = null) {
            val intent = Intent(context, HubActivity::class.java)
            if (nodeId != null) intent.putExtra(EXTRA_NODE, nodeId)
            context.startActivity(intent)
        }
    }
}
