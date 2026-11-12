package com.nuxiva.edge.features.vitals

import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothGatt
import android.bluetooth.BluetoothGattCallback
import android.bluetooth.BluetoothGattCharacteristic
import android.bluetooth.BluetoothGattDescriptor
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothProfile
import android.bluetooth.le.ScanCallback
import android.bluetooth.le.ScanFilter
import android.bluetooth.le.ScanResult
import android.bluetooth.le.ScanSettings
import android.content.Context
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.os.ParcelUuid
import java.util.UUID

@SuppressLint("MissingPermission")
class BleVitalsMonitor(
    private val context: Context,
    private val vault: VitalsVault,
    private val onSamples: (List<VitalSample>) -> Unit,
) {

    private val adapter: BluetoothAdapter? = context.getSystemService(BluetoothManager::class.java)?.adapter
    private val main = Handler(Looper.getMainLooper())
    private val pendingWrites = ArrayDeque<BluetoothGattCharacteristic>()
    private val rr = RrWindow()
    private var gatt: BluetoothGatt? = null
    private var scanning = false
    private var running = false
    private var retryMs = RETRY_MIN_MS

    private val scanCallback = object : ScanCallback() {
        override fun onScanResult(callbackType: Int, result: ScanResult) {
            val known = vault.bleAddress
            if (known.isNotEmpty() && result.device.address != known) return
            stopScan()
            connect(result.device)
        }

        override fun onScanFailed(errorCode: Int) {
            scanning = false
            retryLater()
        }
    }

    private val gattCallback = object : BluetoothGattCallback() {
        override fun onConnectionStateChange(g: BluetoothGatt, status: Int, newState: Int) {
            if (status == BluetoothGatt.GATT_SUCCESS && newState == BluetoothProfile.STATE_CONNECTED) {
                retryMs = RETRY_MIN_MS
                vault.bleAddress = g.device.address
                main.post { g.discoverServices() }
                return
            }
            if (newState == BluetoothProfile.STATE_DISCONNECTED || status != BluetoothGatt.GATT_SUCCESS) {
                g.close()
                if (gatt === g) gatt = null
                synchronized(pendingWrites) { pendingWrites.clear() }
                retryLater()
            }
        }

        override fun onServicesDiscovered(g: BluetoothGatt, status: Int) {
            if (status != BluetoothGatt.GATT_SUCCESS) {
                g.disconnect()
                return
            }
            synchronized(pendingWrites) {
                pendingWrites.clear()
                CHARACTERISTICS.forEach { uuid -> g.services.firstNotNullOfOrNull { it.getCharacteristic(uuid) }?.let { pendingWrites.addLast(it) } }
            }
            next(g)
        }

        override fun onDescriptorWrite(g: BluetoothGatt, descriptor: BluetoothGattDescriptor, status: Int) {
            next(g)
        }

        @Deprecated("Deprecated in API 33")
        override fun onCharacteristicChanged(g: BluetoothGatt, c: BluetoothGattCharacteristic) {
            @Suppress("DEPRECATION")
            decode(c.uuid, c.value ?: return)
        }

        override fun onCharacteristicChanged(g: BluetoothGatt, c: BluetoothGattCharacteristic, value: ByteArray) {
            decode(c.uuid, value)
        }
    }

    private fun next(g: BluetoothGatt) {
        val c = synchronized(pendingWrites) { pendingWrites.removeFirstOrNull() } ?: return
        if (!subscribe(g, c)) next(g)
    }

    private fun subscribe(g: BluetoothGatt, c: BluetoothGattCharacteristic): Boolean {
        g.setCharacteristicNotification(c, true)
        val descriptor = c.getDescriptor(CCC) ?: return false
        val indicate = c.properties and BluetoothGattCharacteristic.PROPERTY_INDICATE != 0
        val value = if (indicate) BluetoothGattDescriptor.ENABLE_INDICATION_VALUE else BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            g.writeDescriptor(descriptor, value) == BluetoothGatt.GATT_SUCCESS
        } else {
            @Suppress("DEPRECATION")
            descriptor.value = value
            @Suppress("DEPRECATION")
            g.writeDescriptor(descriptor)
        }
    }

    private fun decode(uuid: UUID, value: ByteArray) {
        val now = System.currentTimeMillis() / 1000.0
        val samples = when (uuid) {
            HEART_RATE -> VitalsDecoders.heartRate(value, now) +
                listOfNotNull(rr.add(VitalsDecoders.rrIntervals(value))?.let { VitalSample("hrv", it, now) })
            TEMPERATURE -> VitalsDecoders.temperature(value, now)
            PLX_SPOT, PLX_CONTINUOUS -> VitalsDecoders.oximeter(value, now)
            BLOOD_PRESSURE -> VitalsDecoders.bloodPressure(value, now)
            WEIGHT -> VitalsDecoders.weight(value, now)
            BODY -> VitalsDecoders.bodyFat(value, now)
            else -> emptyList()
        }
        if (samples.isNotEmpty()) onSamples(samples)
    }

    private fun connect(device: BluetoothDevice) {
        if (gatt != null) return
        gatt = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            device.connectGatt(context, true, gattCallback, BluetoothDevice.TRANSPORT_LE)
        } else {
            device.connectGatt(context, true, gattCallback)
        }
    }

    private fun retryLater() {
        if (!running) return
        val wait = retryMs
        retryMs = (retryMs * 2).coerceAtMost(RETRY_MAX_MS)
        main.postDelayed({ if (running && gatt == null) begin() }, wait)
    }

    private fun begin() {
        val bt = adapter?.takeIf { it.isEnabled } ?: return retryLater()
        val known = vault.bleAddress
        if (known.isNotEmpty() && BluetoothAdapter.checkBluetoothAddress(known)) {
            connect(bt.getRemoteDevice(known))
            return
        }
        if (scanning) return
        val scanner = bt.bluetoothLeScanner ?: return retryLater()
        val filters = SERVICES.map { ScanFilter.Builder().setServiceUuid(ParcelUuid(it)).build() }
        scanner.startScan(filters, ScanSettings.Builder().setScanMode(ScanSettings.SCAN_MODE_LOW_POWER).build(), scanCallback)
        scanning = true
    }

    fun start() {
        if (running) return
        running = true
        begin()
    }

    private fun stopScan() {
        if (scanning) runCatching { adapter?.bluetoothLeScanner?.stopScan(scanCallback) }
        scanning = false
    }

    fun stop() {
        running = false
        main.removeCallbacksAndMessages(null)
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
        private val BLOOD_PRESSURE = id("2a35")
        private val WEIGHT = id("2a9d")
        private val BODY = id("2a9c")
        private val CCC = id("2902")
        private val CHARACTERISTICS = listOf(HEART_RATE, TEMPERATURE, PLX_SPOT, PLX_CONTINUOUS, BLOOD_PRESSURE, WEIGHT, BODY)
        private val SERVICES = listOf(id("180d"), id("1809"), id("1822"), id("1810"), id("181d"), id("181b"))
        private const val RETRY_MIN_MS = 5_000L
        private const val RETRY_MAX_MS = 300_000L
    }
}
