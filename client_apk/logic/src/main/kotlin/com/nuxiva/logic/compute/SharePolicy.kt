package com.nuxiva.logic.compute

public data class ShareSettings(
    val consent: Boolean = false,
    val killSwitch: Boolean = false,
    val requireCharging: Boolean = true,
    val minBatteryPercent: Int = 40,
    val maxThermalStatus: Int = 1,
    val maxBatteryTempC: Int = 40,
    val unmeteredOnly: Boolean = true,
    val restOnly: Boolean = true,
    val maxJobs: Int = 1,
) {
    val jobLimit: Int get() = maxJobs.coerceIn(MIN_JOBS, MAX_JOBS)

    public companion object {
        public const val MIN_JOBS: Int = 1
        public const val MAX_JOBS: Int = 4
    }
}

public data class PowerSnapshot(
    val batteryPercent: Int,
    val charging: Boolean,
    val thermalStatus: Int?,
    val batteryTempDeciC: Int?,
    val unmetered: Boolean,
    val screenOn: Boolean,
)

public enum class DenyReason {
    KillSwitch,
    NoConsent,
    NotCharging,
    LowBattery,
    TooHot,
    MeteredNetwork,
    InUse,
}

public sealed interface ShareDecision {
    public data object Allowed : ShareDecision
    public data class Denied(val reason: DenyReason) : ShareDecision
}

public object SharePolicy {
    public fun decide(settings: ShareSettings, power: PowerSnapshot): ShareDecision {
        val reason = when {
            settings.killSwitch -> DenyReason.KillSwitch
            !settings.consent -> DenyReason.NoConsent
            settings.requireCharging && !power.charging -> DenyReason.NotCharging
            power.batteryPercent < settings.minBatteryPercent.coerceIn(5, 100) -> DenyReason.LowBattery
            tooHot(settings, power) -> DenyReason.TooHot
            settings.unmeteredOnly && !power.unmetered -> DenyReason.MeteredNetwork
            settings.restOnly && power.screenOn -> DenyReason.InUse
            else -> null
        }
        return if (reason == null) ShareDecision.Allowed else ShareDecision.Denied(reason)
    }

    private fun tooHot(settings: ShareSettings, power: PowerSnapshot): Boolean {
        val status = power.thermalStatus
        if (status != null && status > settings.maxThermalStatus.coerceIn(0, 3)) return true
        val temp = power.batteryTempDeciC
        return temp != null && temp > settings.maxBatteryTempC.coerceIn(25, 50) * 10
    }
}
