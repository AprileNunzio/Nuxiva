package com.nuxiva.edge.node

import android.content.Context
import android.util.Log
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.serialization.builtins.ListSerializer
import kotlinx.serialization.json.Json
import java.io.File
import java.io.IOException

class ProfileStore(context: Context, private val cipher: KeystoreCipher) {
    private val file = File(context.noBackupFilesDir, FILE_NAME)
    private val json = Json { ignoreUnknownKeys = true }
    private val serializer = ListSerializer(NodeProfile.serializer())
    private val state = MutableStateFlow<List<NodeProfile>>(emptyList())
    private val failure = MutableStateFlow<String?>(null)

    val profiles: StateFlow<List<NodeProfile>> = state.asStateFlow()
    val loadFailure: StateFlow<String?> = failure.asStateFlow()

    init {
        load()
    }

    @Synchronized
    fun add(profile: NodeProfile): Boolean {
        val current = state.value
        if (current.size >= MAX_PROFILES || current.any { it.nodeId == profile.nodeId }) return false
        persist(current + profile)
        return true
    }

    @Synchronized
    fun remove(nodeId: String) {
        persist(state.value.filterNot { it.nodeId == nodeId })
    }

    @Synchronized
    fun update(nodeId: String, change: (NodeProfile) -> NodeProfile) {
        persist(state.value.map { if (it.nodeId == nodeId) change(it) else it })
    }

    @Synchronized
    fun wipe() {
        persist(emptyList())
    }

    private fun load() {
        if (!file.isFile) return
        try {
            val plain = cipher.decrypt(file.readBytes())
            state.value = json.decodeFromString(serializer, String(plain, Charsets.UTF_8))
            plain.fill(0)
        } catch (error: Exception) {
            Log.e(TAG, "Vault unreadable, moving it aside", error)
            failure.value = error.javaClass.simpleName
            file.renameTo(File(file.parentFile, "$FILE_NAME.unreadable"))
        }
    }

    private fun persist(next: List<NodeProfile>) {
        val plain = json.encodeToString(serializer, next).toByteArray(Charsets.UTF_8)
        val sealed = cipher.encrypt(plain)
        plain.fill(0)
        val temp = File(file.parentFile, "$FILE_NAME.tmp")
        try {
            temp.writeBytes(sealed)
            if (!temp.renameTo(file)) throw IOException("vault_rename_failed")
        } catch (error: IOException) {
            Log.e(TAG, "Vault write failed", error)
            temp.delete()
            throw error
        }
        state.value = next
    }

    private companion object {
        const val TAG = "NuxivaVault"
        const val FILE_NAME = "nodes.vault"
        const val MAX_PROFILES = 8
    }
}
