package com.nuxiva.edge.ui

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.core.content.ContextCompat
import com.nuxiva.edge.R

object PermissionGuide {
    private data class Entry(val permissions: List<String>, val name: Int, val why: Int, val minSdk: Int = 0)

    private val entries = listOf(
        Entry(listOf(Manifest.permission.RECORD_AUDIO), R.string.perm_mic_name, R.string.perm_mic_why),
        Entry(listOf(Manifest.permission.CAMERA), R.string.perm_cam_name, R.string.perm_cam_why),
        Entry(
            listOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION),
            R.string.perm_loc_name,
            R.string.perm_loc_why
        ),
        Entry(
            listOf(Manifest.permission.POST_NOTIFICATIONS),
            R.string.perm_notif_name,
            R.string.perm_notif_why,
            Build.VERSION_CODES.TIRAMISU
        )
    )

    fun requestable(): List<String> = entries
        .filter { Build.VERSION.SDK_INT >= it.minSdk }
        .flatMap { it.permissions }

    private fun granted(context: Context, entry: Entry): Boolean =
        entry.permissions.any { ContextCompat.checkSelfPermission(context, it) == PackageManager.PERMISSION_GRANTED }

    private fun missing(context: Context): List<Entry> = entries
        .filter { Build.VERSION.SDK_INT >= it.minSdk }
        .filterNot { granted(context, it) }

    fun show(activity: Activity, onClose: () -> Unit): Boolean {
        val absent = missing(activity)
        if (absent.isEmpty() || activity.isFinishing) return false
        val body = buildString {
            append(activity.getString(R.string.perm_guide_intro))
            absent.forEach { append("\n\n• ").append(activity.getString(it.name)).append(": ").append(activity.getString(it.why)) }
            append("\n\n").append(activity.getString(R.string.perm_guide_how))
        }
        AlertDialog.Builder(activity)
            .setTitle(R.string.perm_guide_title)
            .setMessage(body)
            .setCancelable(false)
            .setPositiveButton(R.string.perm_guide_open) { _, _ ->
                val settings = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.fromParts("package", activity.packageName, null))
                runCatching { activity.startActivity(settings) }
                onClose()
            }
            .setNegativeButton(R.string.perm_guide_later) { _, _ -> onClose() }
            .show()
        return true
    }
}
