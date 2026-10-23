package com.nuxiva.edge.features.vitals

import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothGatt
import android.bluetooth.BluetoothGattCallback
import android.bluetooth.BluetoothGattCharacteristic
import android.bluetooth.BluetoothGattDescriptor
import android.bluetooth.BluetoothManager
import android.bluetooth.le.ScanCallback
import android.bluetooth.le.ScanFilter
import android.bluetooth.le.ScanResult
import android.bluetooth.le.ScanSettings
import android.content.Context
import android.os.ParcelUuid
import java.util.UUID

@SuppressLint("MissingPermission")
class BleVitalsMonitor(
    private val context: Context,
    private val vault: VitalsVault,
    private val onSamples: (List<VitalSample>) -> Unit,
) {

    private val adapter: BluetoothAdapter? = context.getSystemService(BluetoothManager::class.java)?.adapter
    private var gatt: BluetoothGatt? = null
    private var scanning = false

    private val scanCallback = object : ScanCallback() {
        override fun onScanResult(callbackType: Int, result: ScanResult) {
            val known = vault.bleAddress
            if (known.isNotEmpty() && result.device.address != known) return
            stopScan()
            connect(result.device)
        }
    }

    private val gattCallback = object : BluetoothGattCallback() {
        override fun onConnectionStateChange(g: BluetoothGatt, status: Int, newState: Int) {
            if (newState == android.bluetooth.BluetoothProfile.STATE_CONNECTED) {
                vault.bleAddress = g.device.address
                g.discoverServices()
            } else {
                g.close()
                if (gatt === g) gatt = null
            }
        }

        override fun onServicesDiscovered(g: BluetoothGatt, status: Int) {
            CHARACTERISTICS.forEach { uuid ->
                g.services.firstNotNullOfOrNull { it.getCharacteristic(uuid) }?.let { subscribe(g, it) }
            }
        }

        @Deprecated("Deprecated in API 33")
        override fun onCharacteristicChanged(g: BluetoothGatt, c: BluetoothGattCharacteristic) {
            decode(c.uuid, c.value ?: return)
        }

        override fun onCharacteristicChanged(g: BluetoothGatt, c: BluetoothGattCharacteristic, value: ByteArray) {
            decode(c.uuid, value)
        }
    }

    private fun subscribe(g: BluetoothGatt, c: BluetoothGattCharacteristic) {
        g.setCharacteristicNotification(c, true)
        val descriptor = c.getDescriptor(CCC) ?: return
        val indicate = c.properties and BluetoothGattCharacteristic.PROPERTY_INDICATE != 0
        val value = if (indicate) BluetoothGattDescriptor.ENABLE_INDICATION_VALUE else BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE
        @Suppress("DEPRECATION")
        descriptor.value = value
        @Suppress("DEPRECATION")
        g.writeDescriptor(descriptor)
    }

    private fun decode(uuid: UUID, value: ByteArray) {
        val now = System.currentTimeMillis() / 1000.0
        val samples = when (uuid) {
            HEART_RATE -> VitalsDecoders.heartRate(value, now)
            TEMPERATURE -> VitalsDecoders.temperature(value, now)
            PLX_SPOT, PLX_CONTINUOUS -> VitalsDecoders.oximeter(value, now)
            else -> emptyList()
        }
        if (samples.isNotEmpty()) onSamples(samples)
    }

    private fun connect(device: BluetoothDevice) {
        gatt = device.connectGatt(context, false, gattCallback)
    }

    fun start() {
        if (gatt != null || scanning) return
        val scanner = adapter?.takeIf { it.isEnabled }?.bluetoothLeScanner ?: return
        val filters = SERVICES.map { ScanFilter.Builder().setServiceUuid(ParcelUuid(it)).build() }
        scanner.startScan(filters, ScanSettings.Builder().setScanMode(ScanSettings.SCAN_MODE_LOW_POWER).build(), scanCallback)
        scanning = true
    }

    private fun stopScan() {
        if (scanning) adapter?.bluetoothLeScanner?.stopScan(scanCallback)
        scanning = false
    }

    fun stop() {
        stopScan()
        gatt?.close()
        gatt = null
    }

    companion object {
        private fun id(short: String) = UUID.fromString("0000$short-0000-1000-8000-00805f9b34fb")
        private val HEART_RATE = id("2a37")
        private val TEMPERATURE = id("2a1c")
        private val PLX_SPOT = id("2a5e")
        private val PLX_CONTINUOUS = id("2a5f")
        private val CCC = id("2902")
        private val CHARACTERISTICS = listOf(HEART_RATE, TEMPERATURE, PLX_SPOT, PLX_CONTINUOUS)
        private val SERVICES = listOf(id("180d"), id("1809"), id("1822"))
    }
}
