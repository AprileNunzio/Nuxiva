package com.nuxiva.logic.net

import java.io.ByteArrayInputStream
import java.security.KeyStore
import java.security.MessageDigest
import java.security.cert.CertificateFactory
import java.security.cert.X509Certificate
import javax.net.ssl.TrustManagerFactory
import javax.net.ssl.X509TrustManager

public class PinMismatchException(message: String) : Exception(message)

public object PinnedTrust {
    private const val ALIAS = "nuxiva-ca"

    public fun parse(pem: String): X509Certificate {
        if (!pem.contains("BEGIN CERTIFICATE")) throw PinMismatchException("ca_invalid")
        return try {
            CertificateFactory.getInstance("X.509")
                .generateCertificate(ByteArrayInputStream(pem.toByteArray(Charsets.US_ASCII))) as X509Certificate
        } catch (_: Exception) {
            throw PinMismatchException("ca_invalid")
        }
    }

    public fun fingerprint(pem: String): String {
        val digest = MessageDigest.getInstance("SHA-256").digest(parse(pem).encoded)
        return digest.joinToString("") { "%02x".format(it.toInt() and 0xFF) }
    }

    public fun matches(expected: String, actual: String): Boolean =
        MessageDigest.isEqual(expected.lowercase().toByteArray(Charsets.US_ASCII), actual.lowercase().toByteArray(Charsets.US_ASCII))

    public fun trustManager(pem: String): X509TrustManager {
        val store = KeyStore.getInstance(KeyStore.getDefaultType()).apply {
            load(null, null)
            setCertificateEntry(ALIAS, parse(pem))
        }
        val factory = TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm())
        factory.init(store)
        return factory.trustManagers.filterIsInstance<X509TrustManager>().firstOrNull()
            ?: throw PinMismatchException("ca_invalid")
    }

    public fun short(fingerprint: String): String =
        fingerprint.take(16).uppercase().chunked(4).joinToString("-")
}
