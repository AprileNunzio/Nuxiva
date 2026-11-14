package com.nuxiva.edge.node

import android.os.Build
import androidx.annotation.RequiresApi
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.security.keystore.StrongBoxUnavailableException
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

class KeystoreCipher(private val alias: String = ALIAS) {

    fun encrypt(plain: ByteArray): ByteArray {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, key())
        cipher.updateAAD(AAD)
        val sealed = cipher.doFinal(plain)
        return byteArrayOf(VERSION) + cipher.iv + sealed
    }

    fun decrypt(blob: ByteArray): ByteArray {
        require(blob.size > 1 + IV_SIZE && blob[0] == VERSION) { "vault_format" }
        val iv = blob.copyOfRange(1, 1 + IV_SIZE)
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(TAG_BITS, iv))
        cipher.updateAAD(AAD)
        return cipher.doFinal(blob, 1 + IV_SIZE, blob.size - 1 - IV_SIZE)
    }

    private fun key(): SecretKey {
        val store = KeyStore.getInstance(PROVIDER).apply { load(null) }
        (store.getKey(alias, null) as? SecretKey)?.let { return it }
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) generateWithStrongBox() else generate(strongBox = false)
    }

    @RequiresApi(Build.VERSION_CODES.P)
    private fun generateWithStrongBox(): SecretKey = try {
        generate(strongBox = true)
    } catch (_: StrongBoxUnavailableException) {
        generate(strongBox = false)
    }

    private fun generate(strongBox: Boolean): SecretKey {
        val spec = KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setKeySize(KEY_BITS)
            .setRandomizedEncryptionRequired(true)
            .apply {
                if (strongBox && Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) setIsStrongBoxBacked(true)
            }
            .build()
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, PROVIDER).apply { init(spec) }.generateKey()
    }

    private companion object {
        const val PROVIDER = "AndroidKeyStore"
        const val ALIAS = "nuxiva_node_vault_v1"
        const val TRANSFORMATION = "AES/GCM/NoPadding"
        const val KEY_BITS = 256
        const val TAG_BITS = 128
        const val IV_SIZE = 12
        const val VERSION: Byte = 1
        val AAD = "nuxiva-vault-v1".toByteArray(Charsets.US_ASCII)
    }
}
