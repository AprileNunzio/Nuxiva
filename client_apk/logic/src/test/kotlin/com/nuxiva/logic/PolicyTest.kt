package com.nuxiva.logic

import com.nuxiva.logic.compute.DenyReason
import com.nuxiva.logic.compute.JobCodec
import com.nuxiva.logic.compute.JobRejected
import com.nuxiva.logic.compute.PowerSnapshot
import com.nuxiva.logic.compute.ShareDecision
import com.nuxiva.logic.compute.SharePolicy
import com.nuxiva.logic.compute.ShareSettings
import com.nuxiva.logic.device.Orientation
import com.nuxiva.logic.device.Turn
import java.util.Base64
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith

class PolicyTest {
    private val ready = PowerSnapshot(80, true, 0, 300, true, false)
    private val on = ShareSettings(consent = true)

    private fun reason(settings: ShareSettings, power: PowerSnapshot): DenyReason? =
        (SharePolicy.decide(settings, power) as? ShareDecision.Denied)?.reason

    @Test
    fun sharingNeedsConsentAndHonoursTheKillSwitchFirst() {
        assertEquals(DenyReason.NoConsent, reason(ShareSettings(), ready))
        assertEquals(DenyReason.KillSwitch, reason(on.copy(killSwitch = true), ready))
        assertEquals(ShareDecision.Allowed, SharePolicy.decide(on, ready))
    }

    @Test
    fun eachConditionBlocksSharing() {
        assertEquals(DenyReason.NotCharging, reason(on, ready.copy(charging = false)))
        assertEquals(DenyReason.LowBattery, reason(on, ready.copy(batteryPercent = 39)))
        assertEquals(DenyReason.TooHot, reason(on, ready.copy(thermalStatus = 2)))
        assertEquals(DenyReason.TooHot, reason(on, ready.copy(batteryTempDeciC = 411)))
        assertEquals(DenyReason.MeteredNetwork, reason(on, ready.copy(unmetered = false)))
        assertEquals(DenyReason.InUse, reason(on, ready.copy(screenOn = true)))
    }

    @Test
    fun relaxedSettingsAllowTheirCases() {
        val relaxed = on.copy(requireCharging = false, unmeteredOnly = false, restOnly = false)
        assertEquals(ShareDecision.Allowed, SharePolicy.decide(relaxed, ready.copy(charging = false, unmetered = false, screenOn = true)))
    }

    @Test
    fun thermalLimitIsClampedSoItCannotBeDisabled() {
        assertEquals(DenyReason.TooHot, reason(on.copy(maxThermalStatus = 99), ready.copy(thermalStatus = 4)))
    }

    @Test
    fun jobsOutsideTheAllowListAreRejected() {
        val id = "a".repeat(32)
        val body = Base64.getEncoder().encodeToString("{}".toByteArray())
        assertEquals("/api/chat", JobCodec.decode(id, "POST", "/api/chat", body).path)
        assertEquals("compute_path_not_allowed", assertFailsWith<JobRejected> { JobCodec.decode(id, "POST", "/api/delete", body) }.code)
        assertEquals("compute_path_not_allowed", assertFailsWith<JobRejected> { JobCodec.decode(id, "GET", "/api/chat", body) }.code)
        assertEquals("compute_invalid_body", assertFailsWith<JobRejected> { JobCodec.decode(id, "POST", "/api/chat", "***") }.code)
        assertEquals("compute_invalid_job", assertFailsWith<JobRejected> { JobCodec.decode("x", "POST", "/api/chat", body) }.code)
        val huge = Base64.getEncoder().encodeToString(ByteArray(JobCodec.BODY_LIMIT + 1))
        assertEquals("compute_body_too_large", assertFailsWith<JobRejected> { JobCodec.decode(id, "POST", "/api/chat", huge) }.code)
    }

    @Test
    fun chunkCarriesErrorAndStatus() {
        val chunk = JobCodec.chunk("a".repeat(32), ByteArray(0), error = "compute_unavailable")
        assertEquals("true", chunk.getValue("done").toString())
        assertEquals("\"compute_unavailable\"", chunk.getValue("error").toString())
    }

    @Test
    fun rotationDirectionFollowsAndroidConvention() {
        assertEquals(Turn.None, Orientation.turn(null, 90))
        assertEquals(Turn.CounterClockwise, Orientation.turn(0, 90))
        assertEquals(Turn.Clockwise, Orientation.turn(0, 270))
        assertEquals(Turn.Flip, Orientation.turn(90, 270))
        assertEquals(Turn.None, Orientation.turn(90, 90))
        assertEquals(270, Orientation.degrees(3))
        val first = Orientation.next(null, 0, 1080, 2400)
        val second = Orientation.next(first, 1, 2400, 1080)
        assertEquals("landscape", second.mode)
        assertEquals(Turn.CounterClockwise, second.turn)
        assertEquals(Turn.CounterClockwise, Orientation.next(second, 1, 2400, 1080).turn)
    }
}
