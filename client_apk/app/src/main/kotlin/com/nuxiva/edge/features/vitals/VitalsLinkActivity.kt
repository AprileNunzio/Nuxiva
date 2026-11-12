package com.nuxiva.edge.features.vitals

import android.Manifest
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.health.connect.client.PermissionController
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import java.net.URI

class VitalsLinkActivity : AppCompatActivity() {

    private val healthPermissions = registerForActivityResult(PermissionController.createRequestPermissionResultContract()) { begin() }

    private val bluetoothPermissions = registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { askHealth() }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val data: Uri? = intent?.data
        val vault = VitalsVault(this)
        val server = data?.getQueryParameter("server").orEmpty()
        val token = data?.getQueryParameter("token").orEmpty()
        if (data != null) {
            if (!VitalsVault.validServer(server) || token.isEmpty()) {
                Toast.makeText(this, "Link Nuxiva non valido", Toast.LENGTH_LONG).show()
                finish()
                return
            }
            confirm(vault, server, token)
            return
        }
        if (!vault.linked()) {
            finish()
            return
        }
        askBluetooth()
    }

    private fun confirm(vault: VitalsVault, server: String, token: String) {
        val host = runCatching { URI(server).host }.getOrNull().orEmpty()
        val clear = server.startsWith("http://")
        AlertDialog.Builder(this)
            .setTitle("Collegare i dati della salute?")
            .setMessage("I parametri della salute verranno inviati a $host." +
                (if (clear) "\nAttenzione: la connessione non è cifrata (http)." else "") +
                (if (vault.linked()) "\nIl collegamento attuale verrà sostituito." else ""))
            .setPositiveButton("Collega") { _, _ ->
                if (vault.link(server, token)) askBluetooth() else {
                    Toast.makeText(this, "Link Nuxiva non valido", Toast.LENGTH_LONG).show()
                    finish()
                }
            }
            .setNegativeButton("Annulla") { _, _ -> finish() }
            .setOnCancelListener { finish() }
            .show()
    }

    private fun askBluetooth() {
        val needed = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            arrayOf(Manifest.permission.BLUETOOTH_SCAN, Manifest.permission.BLUETOOTH_CONNECT)
        } else {
            arrayOf(Manifest.permission.ACCESS_FINE_LOCATION)
        }.filter { ContextCompat.checkSelfPermission(this, it) != android.content.pm.PackageManager.PERMISSION_GRANTED }
        if (needed.isEmpty()) askHealth() else bluetoothPermissions.launch(needed.toTypedArray())
    }

    private fun askHealth() {
        if (!HealthConnectReader.available(this)) {
            begin()
            return
        }
        CoroutineScope(Dispatchers.Main).launch {
            val granted = androidx.health.connect.client.HealthConnectClient.getOrCreate(this@VitalsLinkActivity)
                .permissionController.getGrantedPermissions()
            if (granted.containsAll(HealthConnectReader.PERMISSIONS)) begin() else healthPermissions.launch(HealthConnectReader.PERMISSIONS)
        }
    }

    private fun begin() {
        ContextCompat.startForegroundService(this, Intent(this, VitalsService::class.java))
        Toast.makeText(this, "Parametri vitali collegati a Nuxiva", Toast.LENGTH_LONG).show()
        finish()
    }
}
