package com.nuxiva.edge.features.vitals

import android.content.Context
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.BodyTemperatureRecord
import androidx.health.connect.client.records.HeartRateRecord
import androidx.health.connect.client.records.OxygenSaturationRecord
import androidx.health.connect.client.request.ReadRecordsRequest
import androidx.health.connect.client.time.TimeRangeFilter
import java.time.Duration
import java.time.Instant

class HealthConnectReader(private val context: Context) {

    companion object {
        val PERMISSIONS = setOf(
            HealthPermission.getReadPermission(HeartRateRecord::class),
            HealthPermission.getReadPermission(OxygenSaturationRecord::class),
            HealthPermission.getReadPermission(BodyTemperatureRecord::class),
        )
        private val WINDOW: Duration = Duration.ofMinutes(10)

        fun available(context: Context): Boolean =
            HealthConnectClient.getSdkStatus(context) == HealthConnectClient.SDK_AVAILABLE
    }

    suspend fun read(): List<VitalSample> {
        if (!available(context)) return emptyList()
        val client = HealthConnectClient.getOrCreate(context)
        val granted = client.permissionController.getGrantedPermissions()
        val range = TimeRangeFilter.between(Instant.now().minus(WINDOW), Instant.now())
        val out = mutableListOf<VitalSample>()
        if (HealthPermission.getReadPermission(HeartRateRecord::class) in granted) {
            client.readRecords(ReadRecordsRequest(HeartRateRecord::class, range)).records
                .flatMap { it.samples }
                .forEach { out += VitalSample("heart_rate", it.beatsPerMinute.toDouble(), it.time.epochSecond.toDouble()) }
        }
        if (HealthPermission.getReadPermission(OxygenSaturationRecord::class) in granted) {
            client.readRecords(ReadRecordsRequest(OxygenSaturationRecord::class, range)).records
                .forEach { out += VitalSample("spo2", it.percentage.value, it.time.epochSecond.toDouble()) }
        }
        if (HealthPermission.getReadPermission(BodyTemperatureRecord::class) in granted) {
            client.readRecords(ReadRecordsRequest(BodyTemperatureRecord::class, range)).records
                .forEach { out += VitalSample("body_temp", it.temperature.inCelsius, it.time.epochSecond.toDouble()) }
        }
        return out.sortedBy { it.timestampSeconds }.takeLast(60)
    }
}
