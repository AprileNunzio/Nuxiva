package com.nuxiva.edge.update

import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageInstaller
import android.content.pm.PackageManager
import android.os.Build
import com.nuxiva.edge.BuildConfig
import com.nuxiva.logic.update.UpdateOffer
import com.nuxiva.logic.update.UpdatePolicy
import com.nuxiva.logic.update.UpdateStep
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.serialization.json.JsonElement
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.io.IOException
import java.security.MessageDigest
import java.util.concurrent.TimeUnit

data class UpdateUi(
    val step: UpdateStep = UpdateStep.Idle,
    val offer: UpdateOffer? = null,
    val errorCode: String? = null,
    val errorAt: Long = 0,
    val lastCheck: Long = 0,
    val lastSuccess: Long = 0,
)

enum class InstallStart { Started, NeedsPermission, NotReady }

private class UpdateFailure(val code: String) : Exception(code)

class ApkUpdater(private val context: Context) {
    private val prefs = context.getSharedPreferences(FILE, Context.MODE_PRIVATE)
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val state = MutableStateFlow(initial())
    private var job: Job? = null
    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .followSslRedirects(false)
        .build()

    val ui: StateFlow<UpdateUi> = state.asStateFlow()

    private fun initial(): UpdateUi {
        val pending = prefs.getString(PENDING, null)
        var success = prefs.getLong(SUCCESS, 0)
        if (pending != null && pending == BuildConfig.VERSION_NAME) {
            success = now()
            prefs.edit().putLong(SUCCESS, success).remove(PENDING).apply()
            directory().deleteRecursively()
        }
        return UpdateUi(lastSuccess = success)
    }

    fun noteReply(raw: JsonElement?) {
        val parsed = UpdatePolicy.parse(raw)?.takeIf { UpdatePolicy.isNewer(it.version, BuildConfig.VERSION_NAME) }
        state.update { current ->
            val busy = current.step == UpdateStep.Downloading || current.step == UpdateStep.Installing || current.step == UpdateStep.AwaitingUser
            when {
                busy && parsed != null && current.offer?.version == parsed.version -> current.copy(lastCheck = now())
                busy && parsed != null -> current.copy(lastCheck = now())
                busy -> current.copy(lastCheck = now())
                else -> current.copy(offer = parsed, lastCheck = now(), step = if (current.step == UpdateStep.Failed && parsed == null) UpdateStep.Idle else current.step)
            }
        }
    }

    fun download() {
        val offer = state.value.offer ?: return
        if (job?.isActive == true) return
        job = scope.launch { fetch(offer) }
    }

    fun install(): InstallStart {
        val current = state.value
        val offer = current.offer
        if (current.step != UpdateStep.AwaitingUser || offer == null) return InstallStart.NotReady
        if (!context.packageManager.canRequestPackageInstalls()) return InstallStart.NeedsPermission
        val file = target(offer)
        if (!file.isFile) {
            fail("file_missing")
            return InstallStart.NotReady
        }
        return try {
            commit(file)
            state.update { it.copy(step = UpdateStep.Installing) }
            InstallStart.Started
        } catch (error: IOException) {
            fail("install_session")
            InstallStart.NotReady
        } catch (error: SecurityException) {
            fail("install_denied")
            InstallStart.NotReady
        }
    }

    fun installResult(status: Int) {
        when (status) {
            PackageInstaller.STATUS_SUCCESS -> Unit
            PackageInstaller.STATUS_FAILURE_ABORTED -> state.update { it.copy(step = UpdateStep.AwaitingUser) }
            else -> fail("install_$status")
        }
    }

    private fun fetch(offer: UpdateOffer) {
        state.update { it.copy(step = UpdateStep.Downloading, errorCode = null) }
        val file = target(offer)
        try {
            download(offer, file)
            verify(file, offer)
            prefs.edit().putString(PENDING, offer.version).apply()
            state.update { it.copy(step = UpdateStep.AwaitingUser) }
        } catch (error: UpdateFailure) {
            file.delete()
            fail(error.code)
        } catch (error: IOException) {
            file.delete()
            fail("download_failed")
        }
    }

    private fun download(offer: UpdateOffer, file: File) {
        file.parentFile?.mkdirs()
        val request = Request.Builder().url(offer.url).get().build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) throw UpdateFailure("http_${response.code}")
            val body = response.body ?: throw UpdateFailure("empty_body")
            val limit = offer.sizeBytes ?: UpdatePolicy.MAX_BYTES
            val digest = MessageDigest.getInstance("SHA-256")
            var total = 0L
            file.outputStream().use { out ->
                body.byteStream().use { input ->
                    val buffer = ByteArray(BUFFER)
                    while (true) {
                        val read = input.read(buffer)
                        if (read < 0) break
                        total += read
                        if (total > limit.coerceAtMost(UpdatePolicy.MAX_BYTES)) throw UpdateFailure("too_large")
                        digest.update(buffer, 0, read)
                        out.write(buffer, 0, read)
                    }
                }
            }
            if (total == 0L) throw UpdateFailure("empty_body")
            val actual = digest.digest().joinToString("") { "%02x".format(it) }
            if (!MessageDigest.isEqual(actual.toByteArray(), offer.sha256.toByteArray())) throw UpdateFailure("hash_mismatch")
        }
    }

    private fun verify(file: File, offer: UpdateOffer) {
        val manager = context.packageManager
        val flags = PackageManager.GET_SIGNING_CERTIFICATES
        val archive = manager.getPackageArchiveInfo(file.absolutePath, flags) ?: throw UpdateFailure("not_an_apk")
        if (archive.packageName != context.packageName) throw UpdateFailure("package_mismatch")
        if (archive.longVersionCode <= installedCode(manager)) throw UpdateFailure("version_not_newer")
        if (archive.versionName != offer.version) throw UpdateFailure("version_mismatch")
        val offered = signers(archive) ?: throw UpdateFailure("signature_missing")
        val installed = signers(manager.getPackageInfo(context.packageName, flags)) ?: throw UpdateFailure("signature_missing")
        if (offered.intersect(installed).isEmpty()) throw UpdateFailure("signature_mismatch")
    }

    private fun installedCode(manager: PackageManager): Long =
        manager.getPackageInfo(context.packageName, 0).longVersionCode

    private fun signers(info: android.content.pm.PackageInfo): Set<String>? {
        val signing = info.signingInfo ?: return null
        val list = if (signing.hasMultipleSigners()) signing.apkContentsSigners else signing.signingCertificateHistory
        if (list.isNullOrEmpty()) return null
        return list.map { signature ->
            MessageDigest.getInstance("SHA-256").digest(signature.toByteArray()).joinToString("") { "%02x".format(it) }
        }.toSet()
    }

    private fun commit(file: File) {
        val installer = context.packageManager.packageInstaller
        val params = PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL)
        params.setAppPackageName(context.packageName)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            params.setRequireUserAction(PackageInstaller.SessionParams.USER_ACTION_REQUIRED)
        }
        val id = installer.createSession(params)
        installer.openSession(id).use { session ->
            file.inputStream().use { input ->
                session.openWrite("nuxiva", 0, file.length()).use { out ->
                    input.copyTo(out)
                    session.fsync(out)
                }
            }
            val intent = Intent(context, InstallResultReceiver::class.java).setPackage(context.packageName)
            val flags = PendingIntent.FLAG_UPDATE_CURRENT or if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) PendingIntent.FLAG_MUTABLE else 0
            session.commit(PendingIntent.getBroadcast(context, id, intent, flags).intentSender)
        }
    }

    private fun fail(code: String) {
        val safe = UpdatePolicy.safeCode(code)
        state.update { it.copy(step = UpdateStep.Failed, errorCode = safe, errorAt = now()) }
    }

    private fun directory() = File(context.cacheDir, "updates")

    private fun target(offer: UpdateOffer) = File(directory(), "Nuxiva-${offer.version}.apk")

    private fun now() = System.currentTimeMillis() / 1000L

    private companion object {
        const val FILE = "nuxiva_update"
        const val PENDING = "pending_version"
        const val SUCCESS = "last_success"
        const val BUFFER = 16 * 1024
    }
}
