package com.nuxiva.edge.features.vitals

import android.content.Context
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.ActiveCaloriesBurnedRecord
import androidx.health.connect.client.records.BloodGlucoseRecord
import androidx.health.connect.client.records.BloodPressureRecord
import androidx.health.connect.client.records.BodyFatRecord
import androidx.health.connect.client.records.BodyTemperatureRecord
import androidx.health.connect.client.records.DistanceRecord
import androidx.health.connect.client.records.FloorsClimbedRecord
import androidx.health.connect.client.records.HeartRateRecord
import androidx.health.connect.client.records.HeartRateVariabilityRmssdRecord
import androidx.health.connect.client.records.OxygenSaturationRecord
import androidx.health.connect.client.records.Record
import androidx.health.connect.client.records.RespiratoryRateRecord
import androidx.health.connect.client.records.RestingHeartRateRecord
import androidx.health.connect.client.records.SleepSessionRecord
import androidx.health.connect.client.records.StepsRecord
import androidx.health.connect.client.records.Vo2MaxRecord
import androidx.health.connect.client.records.WeightRecord
import androidx.health.connect.client.request.AggregateRequest
import androidx.health.connect.client.request.ReadRecordsRequest
import androidx.health.connect.client.time.TimeRangeFilter
import java.time.Duration
import java.time.Instant
import java.time.ZoneId
import kotlin.reflect.KClass

class HealthConnectReader(private val context: Context, private val vault: VitalsVault) {

    companion object {
        private val RECORDS: List<KClass<out Record>> = listOf(
            HeartRateRecord::class, RestingHeartRateRecord::class, HeartRateVariabilityRmssdRecord::class,
            OxygenSaturationRecord::class, RespiratoryRateRecord::class, BodyTemperatureRecord::class,
            BloodPressureRecord::class, BloodGlucoseRecord::class, WeightRecord::class, BodyFatRecord::class,
            Vo2MaxRecord::class, StepsRecord::class, ActiveCaloriesBurnedRecord::class, DistanceRecord::class,
            FloorsClimbedRecord::class, SleepSessionRecord::class,
        )
        val PERMISSIONS: Set<String> = RECORDS.map { HealthPermission.getReadPermission(it) }.toSet() +
            HealthPermission.PERMISSION_READ_HEALTH_DATA_IN_BACKGROUND
        private val LIVE_WINDOW: Duration = Duration.ofHours(1)
        private val OVERLAP: Duration = Duration.ofMinutes(15)
        private val SLOW_WINDOW: Duration = Duration.ofDays(30)
        private val DAY_WINDOW: Duration = Duration.ofHours(36)
        private const val MAX_LIVE = 240

        fun available(context: Context): Boolean =
            HealthConnectClient.getSdkStatus(context) == HealthConnectClient.SDK_AVAILABLE
    }

    private lateinit var client: HealthConnectClient
    private lateinit var granted: Set<String>
    private var pending = 0L

    fun commit() {
        if (pending > 0) vault.healthSince = pending
    }

    private fun allowed(type: KClass<out Record>) = HealthPermission.getReadPermission(type) in granted

    private suspend fun <T : Record> records(type: KClass<T>, from: Instant, to: Instant, newestOnly: Boolean = false): List<T> {
        if (!allowed(type)) return emptyList()
        val request = ReadRecordsRequest(type, TimeRangeFilter.between(from, to), ascendingOrder = !newestOnly,
            pageSize = if (newestOnly) 1 else 1000)
        return runCatching { client.readRecords(request).records }.getOrDefault(emptyList())
    }

    private fun seconds(at: Instant) = at.epochSecond.toDouble()

    suspend fun read(): List<VitalSample> {
        if (!available(context)) return emptyList()
        client = HealthConnectClient.getOrCreate(context)
        granted = client.permissionController.getGrantedPermissions()
        val now = Instant.now()
        val since = maxOf(now.minus(LIVE_WINDOW), Instant.ofEpochSecond(vault.healthSince).minus(OVERLAP))
        val out = mutableListOf<VitalSample>()
        records(HeartRateRecord::class, since, now).flatMap { it.samples }
            .forEach { out += VitalSample("heart_rate", it.beatsPerMinute.toDouble(), seconds(it.time)) }
        records(OxygenSaturationRecord::class, now.minus(Duration.ofHours(6)), now, true)
            .forEach { out += VitalSample("spo2", it.percentage.value, seconds(it.time)) }
        records(BodyTemperatureRecord::class, now.minus(Duration.ofHours(6)), now, true)
            .forEach { out += VitalSample("body_temp", it.temperature.inCelsius, seconds(it.time)) }
        records(RestingHeartRateRecord::class, now.minus(DAY_WINDOW), now, true)
            .forEach { out += VitalSample("resting_hr", it.beatsPerMinute.toDouble(), seconds(it.time)) }
        records(HeartRateVariabilityRmssdRecord::class, now.minus(DAY_WINDOW), now, true)
            .forEach { out += VitalSample("hrv", it.heartRateVariabilityMillis, seconds(it.time)) }
        records(RespiratoryRateRecord::class, now.minus(DAY_WINDOW), now, true)
            .forEach { out += VitalSample("resp_rate", it.rate, seconds(it.time)) }
        records(BloodPressureRecord::class, now.minus(Duration.ofDays(7)), now, true).forEach {
            out += VitalSample("bp_sys", it.systolic.inMillimetersOfMercury, seconds(it.time))
            out += VitalSample("bp_dia", it.diastolic.inMillimetersOfMercury, seconds(it.time))
        }
        records(BloodGlucoseRecord::class, now.minus(DAY_WINDOW), now, true)
            .forEach { out += VitalSample("glucose", it.level.inMilligramsPerDeciliter, seconds(it.time)) }
        records(WeightRecord::class, now.minus(SLOW_WINDOW), now, true)
            .forEach { out += VitalSample("weight", it.weight.inKilograms, seconds(it.time)) }
        records(BodyFatRecord::class, now.minus(SLOW_WINDOW), now, true)
            .forEach { out += VitalSample("body_fat", it.percentage.value, seconds(it.time)) }
        records(Vo2MaxRecord::class, now.minus(SLOW_WINDOW), now, true)
            .forEach { out += VitalSample("vo2max", it.vo2MillilitersPerMinuteKilogram, seconds(it.time)) }
        out += today(now)
        out += lastNight(now)
        pending = now.epochSecond
        val live = out.filter { it.metric == "heart_rate" }.sortedBy { it.timestampSeconds }.takeLast(MAX_LIVE)
        return live + out.filter { it.metric != "heart_rate" }
    }

    private suspend fun today(now: Instant): List<VitalSample> {
        val midnight = now.atZone(ZoneId.systemDefault()).toLocalDate().atStartOfDay(ZoneId.systemDefault()).toInstant()
        val metrics = buildSet {
            if (allowed(StepsRecord::class)) add(StepsRecord.COUNT_TOTAL)
            if (allowed(ActiveCaloriesBurnedRecord::class)) add(ActiveCaloriesBurnedRecord.ACTIVE_CALORIES_TOTAL)
            if (allowed(DistanceRecord::class)) add(DistanceRecord.DISTANCE_TOTAL)
            if (allowed(FloorsClimbedRecord::class)) add(FloorsClimbedRecord.FLOORS_CLIMBED_TOTAL)
        }
        if (metrics.isEmpty()) return emptyList()
        val result = runCatching { client.aggregate(AggregateRequest(metrics, TimeRangeFilter.between(midnight, now))) }.getOrNull()
            ?: return emptyList()
        val at = seconds(now)
        return listOfNotNull(
            result[StepsRecord.COUNT_TOTAL]?.let { VitalSample("steps", it.toDouble(), at) },
            result[ActiveCaloriesBurnedRecord.ACTIVE_CALORIES_TOTAL]?.let { VitalSample("active_kcal", it.inKilocalories, at) },
            result[DistanceRecord.DISTANCE_TOTAL]?.let { VitalSample("distance_km", it.inKilometers, at) },
            result[FloorsClimbedRecord.FLOORS_CLIMBED_TOTAL]?.let { VitalSample("floors", it, at) },
        )
    }

    private suspend fun lastNight(now: Instant): List<VitalSample> {
        val sessions = records(SleepSessionRecord::class, now.minus(DAY_WINDOW), now)
        val night = sessions.maxByOrNull { Duration.between(it.startTime, it.endTime) } ?: return emptyList()
        val total = Duration.between(night.startTime, night.endTime).toMinutes().toDouble()
        val minutesOf = { stage: Int ->
            night.stages.filter { it.stage == stage }.sumOf { Duration.between(it.startTime, it.endTime).toMinutes() }.toDouble()
        }
        val awake = minutesOf(SleepSessionRecord.STAGE_TYPE_AWAKE)
        val at = seconds(night.endTime)
        val rows = mutableListOf(VitalSample("sleep_min", (total - awake).coerceAtLeast(0.0), at))
        if (night.stages.isNotEmpty()) {
            rows += VitalSample("sleep_deep_min", minutesOf(SleepSessionRecord.STAGE_TYPE_DEEP), at)
            rows += VitalSample("sleep_rem_min", minutesOf(SleepSessionRecord.STAGE_TYPE_REM), at)
        }
        return rows
    }
}
