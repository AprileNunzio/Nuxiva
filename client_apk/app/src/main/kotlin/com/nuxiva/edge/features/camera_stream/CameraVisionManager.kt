package com.nuxiva.edge.features.camera_stream

import android.content.Context
import android.graphics.ImageFormat
import android.hardware.camera2.*
import android.media.ImageReader
import android.os.Handler
import android.os.HandlerThread
import android.util.Log
import com.nuxiva.edge.features.sensor_uplink.SensorUplink
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

class CameraVisionManager(private val context: Context, private val uplink: SensorUplink) {

    private var cameraDevice: CameraDevice? = null
    private var captureSession: CameraCaptureSession? = null
    private var imageReader: ImageReader? = null
    private var backgroundThread: HandlerThread? = null
    private var backgroundHandler: Handler? = null

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var isStreaming = false

    fun startCameraCapture() {
        startBackgroundThread()
        val manager = context.getSystemService(Context.CAMERA_SERVICE) as CameraManager
        try {
            val cameraId = manager.cameraIdList.firstOrNull { id ->
                val chars = manager.getCameraCharacteristics(id)
                val facing = chars.get(CameraCharacteristics.LENS_FACING)
                facing == CameraCharacteristics.LENS_FACING_FRONT || facing == CameraCharacteristics.LENS_FACING_BACK
            } ?: return

            imageReader = ImageReader.newInstance(640, 480, ImageFormat.JPEG, 2).apply {
                setOnImageAvailableListener({ reader ->
                    val image = reader.acquireLatestImage() ?: return@setOnImageAvailableListener
                    val planes = image.planes
                    val buffer = planes[0].buffer
                    val bytes = ByteArray(buffer.remaining())
                    buffer.get(bytes)
                    image.close()

                    if (isStreaming) {
                        dispatchFrameToServer(bytes)
                    }
                }, backgroundHandler)
            }

            manager.openCamera(cameraId, object : CameraDevice.StateCallback() {
                override fun onOpened(camera: CameraDevice) {
                    cameraDevice = camera
                    createCaptureSession()
                }

                override fun onDisconnected(camera: CameraDevice) {
                    camera.close()
                    cameraDevice = null
                }

                override fun onError(camera: CameraDevice, error: Int) {
                    camera.close()
                    cameraDevice = null
                }
            }, backgroundHandler)
            isStreaming = true
        } catch (error: SecurityException) {
            Log.w(TAG, "Camera permission missing: ${error.message}")
        } catch (error: CameraAccessException) {
            Log.w(TAG, "Camera unavailable: ${error.reason}")
        }
    }

    private fun createCaptureSession() {
        val readerSurface = imageReader?.surface ?: return
        try {
            val builder = cameraDevice?.createCaptureRequest(CameraDevice.TEMPLATE_PREVIEW)?.apply {
                addTarget(readerSurface)
                set(CaptureRequest.CONTROL_AF_MODE, CaptureRequest.CONTROL_AF_MODE_CONTINUOUS_PICTURE)
            } ?: return

            cameraDevice?.createCaptureSession(
                listOf(readerSurface),
                object : CameraCaptureSession.StateCallback() {
                    override fun onConfigured(session: CameraCaptureSession) {
                        captureSession = session
                        try {
                            session.setRepeatingRequest(builder.build(), null, backgroundHandler)
                        } catch (error: CameraAccessException) {
                            Log.w(TAG, "Camera capture refused: ${error.reason}")
                        }
                    }

                    override fun onConfigureFailed(session: CameraCaptureSession) {
                        Log.w(TAG, "Camera session configuration failed")
                    }
                },
                backgroundHandler
            )
        } catch (error: CameraAccessException) {
            Log.w(TAG, "Camera session unavailable: ${error.reason}")
        }
    }

    private fun dispatchFrameToServer(jpegBytes: ByteArray) {
        scope.launch { uplink.frame(jpegBytes) }
    }

    fun stopCameraCapture() {
        isStreaming = false
        try {
            captureSession?.close()
            captureSession = null
            cameraDevice?.close()
            cameraDevice = null
            imageReader?.close()
            imageReader = null
        } catch (error: IllegalStateException) {
            Log.w(TAG, "Camera close failed: ${error.message}")
        }
        stopBackgroundThread()
    }

    private fun startBackgroundThread() {
        backgroundThread = HandlerThread("NuxivaCameraBackground").also { it.start() }
        backgroundHandler = Handler(backgroundThread?.looper ?: return)
    }

    private fun stopBackgroundThread() {
        backgroundThread?.quitSafely()
        try {
            backgroundThread?.join()
            backgroundThread = null
            backgroundHandler = null
        } catch (error: InterruptedException) {
            Thread.currentThread().interrupt()
            Log.w(TAG, "Camera thread stop interrupted")
        }
    }

    private companion object {
        const val TAG = "NuxivaCamera"
    }
}
