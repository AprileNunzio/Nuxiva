package com.nuxiva.edge.hub

import android.annotation.SuppressLint
import android.content.Context
import android.net.Uri
import android.net.http.SslCertificate
import android.net.http.SslError
import android.webkit.CookieManager
import android.webkit.PermissionRequest
import android.webkit.SslErrorHandler
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import com.nuxiva.edge.node.NodeProfile
import com.nuxiva.logic.net.PinnedTrust
import java.io.ByteArrayInputStream
import java.security.cert.CertificateFactory
import java.security.cert.X509Certificate
import javax.net.ssl.X509TrustManager

interface HubHost {
    fun microphoneAllowed(): Boolean
    fun cameraAllowed(): Boolean
    fun ensureDevicePermissions(audio: Boolean, video: Boolean, result: (Boolean) -> Unit)
    fun onMediaGranted(audio: Boolean, video: Boolean)
    fun onMediaReleased()
    fun onLoaded()
    fun onFailure(code: String)
}

@SuppressLint("SetJavaScriptEnabled")
fun hubWebView(context: Context, profile: NodeProfile, host: HubHost): WebView {
    val server = Uri.parse(profile.server)
    val trust = PinnedTrust.trustManager(profile.caPem)
    return WebView(context).apply {
        settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            allowFileAccess = false
            allowContentAccess = false
            @Suppress("DEPRECATION")
            allowFileAccessFromFileURLs = false
            @Suppress("DEPRECATION")
            allowUniversalAccessFromFileURLs = false
            mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
            mediaPlaybackRequiresUserGesture = false
            setSupportMultipleWindows(false)
            setGeolocationEnabled(false)
            safeBrowsingEnabled = true
            textZoom = 100
        }
        isLongClickable = false
        setBackgroundColor(android.graphics.Color.BLACK)
        val self = this
        CookieManager.getInstance().apply {
            setAcceptCookie(true)
            setAcceptThirdPartyCookies(self, false)
        }
        webViewClient = guarded(server, trust, host)
        webChromeClient = mediaGate(server, host)
    }
}

private fun sameOrigin(uri: Uri?, server: Uri): Boolean =
    uri != null && uri.scheme == "https" && uri.host.equals(server.host, ignoreCase = true) && portOf(uri) == portOf(server)

private fun portOf(uri: Uri): Int = if (uri.port == -1) 443 else uri.port

private fun guarded(server: Uri, trust: X509TrustManager, host: HubHost) = object : WebViewClient() {
    override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean = !sameOrigin(request.url, server)

    override fun shouldInterceptRequest(view: WebView, request: WebResourceRequest): WebResourceResponse? {
        val uri = request.url
        if (sameOrigin(uri, server) || uri.scheme in LOCAL_SCHEMES) return null
        return WebResourceResponse("text/plain", "utf-8", 403, "Blocked", emptyMap(), ByteArrayInputStream(ByteArray(0)))
    }

    override fun onReceivedSslError(view: WebView, handler: SslErrorHandler, error: SslError) {
        if (sameOrigin(Uri.parse(error.url), server) && trusted(error.certificate, trust)) handler.proceed() else {
            handler.cancel()
            host.onFailure("tls")
        }
    }

    override fun onReceivedError(view: WebView, request: WebResourceRequest, error: WebResourceError) {
        if (request.isForMainFrame) host.onFailure("page_${error.errorCode}")
    }

    override fun onPageFinished(view: WebView, url: String?) {
        if (sameOrigin(Uri.parse(url.orEmpty()), server)) host.onLoaded()
    }
}

private fun mediaGate(server: Uri, host: HubHost) = object : WebChromeClient() {
    override fun onPermissionRequest(request: PermissionRequest) {
        val wanted = request.resources.toSet()
        val audio = PermissionRequest.RESOURCE_AUDIO_CAPTURE in wanted
        val video = PermissionRequest.RESOURCE_VIDEO_CAPTURE in wanted
        val onlyCapture = wanted.all { it == PermissionRequest.RESOURCE_AUDIO_CAPTURE || it == PermissionRequest.RESOURCE_VIDEO_CAPTURE }
        val grantAudio = audio && host.microphoneAllowed()
        val grantVideo = video && host.cameraAllowed()
        if (!sameOrigin(request.origin, server) || !onlyCapture || (!grantAudio && !grantVideo)) {
            request.deny()
            return
        }
        host.ensureDevicePermissions(grantAudio, grantVideo) { allowed ->
            if (!allowed) {
                request.deny()
                return@ensureDevicePermissions
            }
            val resources = buildList {
                if (grantAudio) add(PermissionRequest.RESOURCE_AUDIO_CAPTURE)
                if (grantVideo) add(PermissionRequest.RESOURCE_VIDEO_CAPTURE)
            }
            request.grant(resources.toTypedArray())
            host.onMediaGranted(grantAudio, grantVideo)
        }
    }

    override fun onPermissionRequestCanceled(request: PermissionRequest) {
        host.onMediaReleased()
    }
}

private fun trusted(certificate: SslCertificate, trust: X509TrustManager): Boolean {
    val der = SslCertificate.saveState(certificate).getByteArray(CERTIFICATE_KEY) ?: return false
    return try {
        val leaf = CertificateFactory.getInstance("X.509").generateCertificate(ByteArrayInputStream(der)) as X509Certificate
        val authType = if (leaf.publicKey.algorithm == "EC") "ECDHE_ECDSA" else "RSA"
        trust.checkServerTrusted(arrayOf(leaf), authType)
        true
    } catch (_: Exception) {
        false
    }
}

private const val CERTIFICATE_KEY = "x509-certificate"
private val LOCAL_SCHEMES = setOf("data", "blob", "about")
