package com.nuxiva.edge.features.vitals

import kotlin.math.pow
import kotlin.math.roundToInt

data class VitalSample(val metric: String, val value: Double, val timestampSeconds: Double)

object VitalsDecoders {

    private val sfloatSpecial = setOf(0x07FF, 0x0800, 0x0801, 0x07FE, 0x0802)
    private val floatSpecial = setOf(0x007FFFFF, 0x00800000, 0x00800001, 0x007FFFFE, 0x00800002)

    private fun u16(data: ByteArray, at: Int): Int = (data[at].toInt() and 0xFF) or ((data[at + 1].toInt() and 0xFF) shl 8)

    private fun u32(data: ByteArray, at: Int): Long =
        (0 until 4).fold(0L) { acc, i -> acc or ((data[at + i].toLong() and 0xFF) shl (8 * i)) }

    private fun sfloat(raw: Int): Double? {
        if (raw in sfloatSpecial) return null
        var mantissa = raw and 0x0FFF
        var exponent = raw shr 12
        if (mantissa >= 0x800) mantissa -= 0x1000
        if (exponent >= 0x8) exponent -= 0x10
        return mantissa * 10.0.pow(exponent)
    }

    private fun ieeeFloat(raw: Long): Double? {
        if (raw.toInt() in floatSpecial) return null
        var mantissa = (raw and 0xFFFFFF).toInt()
        var exponent = (raw shr 24).toInt()
        if (mantissa >= 0x800000) mantissa -= 0x1000000
        if (exponent >= 0x80) exponent -= 0x100
        return mantissa * 10.0.pow(exponent)
    }

    fun heartRate(data: ByteArray, now: Double): List<VitalSample> {
        val wide = data.isNotEmpty() && (data[0].toInt() and 1) == 1
        if (data.size < if (wide) 3 else 2) return emptyList()
        val bpm = if (wide) u16(data, 1) else data[1].toInt() and 0xFF
        return listOf(VitalSample("heart_rate", bpm.toDouble(), now))
    }

    fun temperature(data: ByteArray, now: Double): List<VitalSample> {
        if (data.size < 5) return emptyList()
        val value = ieeeFloat(u32(data, 1)) ?: return emptyList()
        val celsius = if ((data[0].toInt() and 1) == 1) (value - 32) * 5 / 9 else value
        return listOf(VitalSample("body_temp", (celsius * 10).roundToInt() / 10.0, now))
    }

    fun oximeter(data: ByteArray, now: Double): List<VitalSample> {
        if (data.size < 5) return emptyList()
        val spo2 = sfloat(u16(data, 1))
        val pulse = sfloat(u16(data, 3))
        return listOfNotNull(
            spo2?.let { VitalSample("spo2", it.roundToInt().toDouble(), now) },
            pulse?.let { VitalSample("heart_rate", it.roundToInt().toDouble(), now) },
        )
    }
}
