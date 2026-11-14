package com.nuxiva.edge.node

import com.nuxiva.logic.net.PinnedTrust
import okhttp3.ConnectionSpec
import okhttp3.OkHttpClient
import java.security.SecureRandom
import java.security.cert.X509Certificate
import java.util.concurrent.TimeUnit
import javax.net.ssl.SSLContext
import javax.net.ssl.TrustManager
import javax.net.ssl.X509TrustManager

object TlsClients {

    fun pinned(caPem: String): OkHttpClient {
        val trust = PinnedTrust.trustManager(caPem)
        return build(trust)
    }

    fun firstContact(): OkHttpClient = build(AcceptAny)

    private fun build(trust: X509TrustManager): OkHttpClient {
        val context = SSLContext.getInstance("TLS").apply { init(null, arrayOf<TrustManager>(trust), SecureRandom()) }
        return OkHttpClient.Builder()
            .sslSocketFactory(context.socketFactory, trust)
            .hostnameVerifier { _, _ -> true }
            .connectionSpecs(listOf(ConnectionSpec.MODERN_TLS))
            .followRedirects(false)
            .followSslRedirects(false)
            .retryOnConnectionFailure(false)
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .build()
    }

    private object AcceptAny : X509TrustManager {
        override fun checkClientTrusted(chain: Array<out X509Certificate>?, authType: String?) = Unit
        override fun checkServerTrusted(chain: Array<out X509Certificate>?, authType: String?) = Unit
        override fun getAcceptedIssuers(): Array<X509Certificate> = emptyArray()
    }
}
