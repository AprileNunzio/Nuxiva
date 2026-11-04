package com.nuxiva.edge.features.vitals

import kotlin.math.abs
import kotlin.math.pow
import kotlin.math.sqrt
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
        return if (bpm > 0) listOf(VitalSample("heart_rate", bpm.toDouble(), now)) else emptyList()
    }

    fun rrIntervals(data: ByteArray): List<Double> {
        if (data.isEmpty()) return emptyList()
        val flags = data[0].toInt() and 0xFF
        if (flags and 0x10 == 0) return emptyList()
        var at = if (flags and 1 == 1) 3 else 2
        if (flags and 0x08 != 0) at += 2
        val out = mutableListOf<Double>()
        while (at + 2 <= data.size) {
            val ms = u16(data, at) * 1000.0 / 1024.0
            if (ms in 250.0..2400.0) out += ms
            at += 2
        }
        return out
    }

    fun bloodPressure(data: ByteArray, now: Double): List<VitalSample> {
        if (data.size < 7) return emptyList()
        val flags = data[0].toInt() and 0xFF
        val scale = if (flags and 1 == 1) KPA_TO_MMHG else 1.0
        val sys = sfloat(u16(data, 1)) ?: return emptyList()
        val dia = sfloat(u16(data, 3)) ?: return emptyList()
        val rows = mutableListOf(
            VitalSample("bp_sys", (sys * scale).roundToInt().toDouble(), now),
            VitalSample("bp_dia", (dia * scale).roundToInt().toDouble(), now),
        )
        val at = 7 + if (flags and 0x02 != 0) 7 else 0
        if (flags and 0x04 != 0 && data.size >= at + 2) {
            sfloat(u16(data, at))?.takeIf { it > 0 }?.let { rows += VitalSample("heart_rate", it.roundToInt().toDouble(), now) }
        }
        return rows
    }

    fun weight(data: ByteArray, now: Double): List<VitalSample> {
        if (data.size < 3) return emptyList()
        val raw = u16(data, 1)
        if (raw == 0xFFFF) return emptyList()
        val kg = if ((data[0].toInt() and 1) == 1) raw * 0.01 * LB_TO_KG else raw * 0.005
        return listOf(VitalSample("weight", (kg * 10).roundToInt() / 10.0, now))
    }

    fun bodyFat(data: ByteArray, now: Double): List<VitalSample> {
        if (data.size < 4) return emptyList()
        val raw = u16(data, 2)
        return if (raw == 0xFFFF) emptyList() else listOf(VitalSample("body_fat", raw / 10.0, now))
    }

    private const val KPA_TO_MMHG = 7.50062
    private const val LB_TO_KG = 0.45359237

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

class RrWindow {
    private val rows = ArrayDeque<Double>()
    private var fresh = 0

    fun add(intervals: List<Double>): Double? {
        intervals.forEach { ms ->
            val last = rows.lastOrNull()
            if (last != null && abs(ms - last) > last * 0.3) return@forEach
            rows.addLast(ms)
            if (rows.size > WINDOW) rows.removeFirst()
            fresh++
        }
        if (rows.size < MIN || fresh < MIN) return null
        fresh = 0
        val diffs = rows.zipWithNext { a, b -> (b - a) * (b - a) }
        return Math.round(sqrt(diffs.average())).toDouble()
    }

    companion object {
        private const val WINDOW = 60
        private const val MIN = 20
    }
}
