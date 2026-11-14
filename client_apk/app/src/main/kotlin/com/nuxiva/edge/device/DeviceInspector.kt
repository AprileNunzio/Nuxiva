package com.nuxiva.edge.device

import android.app.ActivityManager
import android.content.Context
import android.content.pm.PackageManager
import android.hardware.Sensor
import android.hardware.SensorManager
import android.hardware.camera2.CameraAccessException
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraManager
import android.os.Build
import android.util.Log
import com.nuxiva.logic.device.DeviceFacts
import com.nuxiva.logic.device.DisplayFacts

class DeviceInspector(private val context: Context, private val orientation: OrientationMonitor) {

    fun facts(): DeviceFacts {
        val memory = ActivityManager.MemoryInfo().also { context.getSystemService(ActivityManager::class.java).getMemoryInfo(it) }
        val metrics = orientation.displayMetrics()
        val packages = context.packageManager
        return DeviceFacts(
            manufacturer = Build.MANUFACTURER.orEmpty(),
            model = Build.MODEL.orEmpty(),
            socVendor = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) Build.SOC_MANUFACTURER else Build.MANUFACTURER.orEmpty(),
            socModel = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) Build.SOC_MODEL else Build.HARDWARE.orEmpty(),
            abi = Build.SUPPORTED_ABIS.firstOrNull().orEmpty(),
            cores = Runtime.getRuntime().availableProcessors(),
            ramMb = memory.totalMem / (1024L * 1024L),
            gpu = GpuProbe.renderer(),
            androidRelease = Build.VERSION.RELEASE.orEmpty(),
            sdk = Build.VERSION.SDK_INT,
            sensors = sensors(),
            cameras = cameras(),
            hasMicrophone = packages.hasSystemFeature(PackageManager.FEATURE_MICROPHONE),
            hasBluetooth = packages.hasSystemFeature(PackageManager.FEATURE_BLUETOOTH),
            display = DisplayFacts(metrics.widthPixels, metrics.heightPixels, metrics.densityDpi, orientation.refreshRate()),
            orientation = orientation.current.value,
        )
    }

    fun availableRamMb(): Long {
        val memory = ActivityManager.MemoryInfo().also { context.getSystemService(ActivityManager::class.java).getMemoryInfo(it) }
        return memory.availMem / (1024L * 1024L)
    }

    private fun sensors(): List<String> {
        val manager = context.getSystemService(SensorManager::class.java)
        return manager.getSensorList(Sensor.TYPE_ALL)
            .map { it.stringType.substringAfterLast('.').replace('_', ' ') }
            .distinct()
            .sorted()
    }

    private fun cameras(): List<String> {
        val manager = context.getSystemService(CameraManager::class.java)
        return try {
            manager.cameraIdList.mapNotNull { id ->
                when (manager.getCameraCharacteristics(id).get(CameraCharacteristics.LENS_FACING)) {
                    CameraCharacteristics.LENS_FACING_BACK -> "back camera"
                    CameraCharacteristics.LENS_FACING_FRONT -> "front camera"
                    CameraCharacteristics.LENS_FACING_EXTERNAL -> "external camera"
                    else -> null
                }
            }
        } catch (error: CameraAccessException) {
            Log.w(TAG, "Camera list unavailable", error)
            emptyList()
        }
    }

    private companion object {
        const val TAG = "NuxivaDevice"
    }
}
