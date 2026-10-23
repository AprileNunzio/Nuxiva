package com.nuxiva.edge.features.vitals

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import java.net.URI

class VitalsVault(context: Context) {

    private val prefs: SharedPreferences = EncryptedSharedPreferences.create(
        context,
        FILE,
        MasterKey.Builder(context).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build(),
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
    )

    val server: String get() = prefs.getString(KEY_SERVER, "").orEmpty()
    val token: String get() = prefs.getString(KEY_TOKEN, "").orEmpty()
    var bleAddress: String
        get() = prefs.getString(KEY_BLE, "").orEmpty()
        set(value) = prefs.edit().putString(KEY_BLE, value).apply()

    fun linked(): Boolean = server.isNotEmpty() && token.isNotEmpty()

    fun link(server: String, token: String): Boolean {
        if (!validServer(server) || !TOKEN.matches(token)) return false
        prefs.edit().putString(KEY_SERVER, server.trimEnd('/')).putString(KEY_TOKEN, token).putString(KEY_BLE, "").apply()
        return true
    }

    fun unlink() = prefs.edit().clear().apply()

    companion object {
        private const val FILE = "nuxiva_vitals_vault"
        private const val KEY_SERVER = "server"
        private const val KEY_TOKEN = "token"
        private const val KEY_BLE = "ble"
        private val TOKEN = Regex("^[A-Za-z0-9_-]{20,80}$")

        fun validServer(value: String): Boolean = runCatching {
            val uri = URI(value)
            (uri.scheme == "https" || uri.scheme == "http") && !uri.host.isNullOrEmpty() && uri.userInfo == null
        }.getOrDefault(false)
    }
}
