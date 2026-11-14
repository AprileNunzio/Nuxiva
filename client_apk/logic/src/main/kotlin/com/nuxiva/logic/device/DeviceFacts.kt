package com.nuxiva.logic.device

public data class DisplayFacts(
    val widthPx: Int,
    val heightPx: Int,
    val densityDpi: Int,
    val refreshHz: Int,
)

public data class DeviceFacts(
    val manufacturer: String,
    val model: String,
    val socVendor: String,
    val socModel: String,
    val abi: String,
    val cores: Int,
    val ramMb: Long,
    val gpu: String,
    val androidRelease: String,
    val sdk: Int,
    val sensors: List<String>,
    val cameras: List<String>,
    val hasMicrophone: Boolean,
    val hasBluetooth: Boolean,
    val display: DisplayFacts,
    val orientation: OrientationState,
)
