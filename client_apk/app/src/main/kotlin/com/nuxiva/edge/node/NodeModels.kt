package com.nuxiva.edge.node

import kotlinx.serialization.Serializable

@Serializable
data class NodeProfile(
    val nodeId: String,
    val name: String,
    val server: String,
    val token: String,
    val caPem: String,
    val pin: String,
    val seedHex: String,
    val enrolledAt: Long,
    val enabled: Boolean = true,
)

sealed interface LinkState {
    data object Idle : LinkState
    data object Connecting : LinkState
    data class Online(val lastSeen: Long) : LinkState
    data class Offline(val code: String) : LinkState
    data object Revoked : LinkState
    data class SecurityAlert(val detail: String) : LinkState
}

sealed class NodeFailure(val code: String) : Exception(code) {
    class Unauthorized(code: String) : NodeFailure(code)
    class SignatureRejected(code: String) : NodeFailure(code)
    class Server(code: String, val status: Int) : NodeFailure(code)
    class Unreachable(code: String) : NodeFailure(code)
    class Pin(code: String) : NodeFailure(code)
}

sealed interface RuntimeEvent {
    data class Identify(val nodeId: String) : RuntimeEvent
}
