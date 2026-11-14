package com.nuxiva.edge.ui

import androidx.annotation.StringRes
import com.nuxiva.edge.R
import com.nuxiva.edge.node.LinkState
import com.nuxiva.logic.compute.DenyReason
import com.nuxiva.logic.device.Turn

@StringRes
fun linkLabel(state: LinkState?): Int = when (state) {
    null, LinkState.Idle -> R.string.link_idle
    LinkState.Connecting -> R.string.link_connecting
    is LinkState.Online -> R.string.link_online
    is LinkState.Offline -> R.string.link_offline
    LinkState.Revoked -> R.string.link_revoked
    is LinkState.SecurityAlert -> R.string.link_security
}

@StringRes
fun denyLabel(reason: DenyReason): Int = when (reason) {
    DenyReason.KillSwitch -> R.string.deny_kill
    DenyReason.NoConsent -> R.string.deny_consent
    DenyReason.NotCharging -> R.string.deny_charging
    DenyReason.LowBattery -> R.string.deny_battery
    DenyReason.TooHot -> R.string.deny_hot
    DenyReason.MeteredNetwork -> R.string.deny_metered
    DenyReason.InUse -> R.string.deny_in_use
}

@StringRes
fun turnLabel(turn: Turn): Int = when (turn) {
    Turn.None -> R.string.turn_none
    Turn.Clockwise -> R.string.turn_cw
    Turn.CounterClockwise -> R.string.turn_ccw
    Turn.Flip -> R.string.turn_flip
}

@StringRes
fun errorLabel(code: String): Int = when (code) {
    "enroll_file_invalid" -> R.string.error_file_invalid
    "enroll_code_invalid" -> R.string.error_code_invalid
    "enroll_file_expired" -> R.string.error_file_expired
    "enroll_token_invalid" -> R.string.error_token_invalid
    "enroll_node_exists" -> R.string.error_node_exists
    "enroll_pin_mismatch", "enroll_ca_invalid" -> R.string.error_pin_mismatch
    "enroll_unreachable" -> R.string.error_unreachable
    "enroll_too_many_nodes" -> R.string.error_too_many
    "rate_limited" -> R.string.error_rate_limited
    else -> R.string.error_generic
}
