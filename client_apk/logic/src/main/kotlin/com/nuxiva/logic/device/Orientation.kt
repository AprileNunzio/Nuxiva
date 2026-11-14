package com.nuxiva.logic.device

public enum class Turn(public val wire: String) {
    None("none"),
    Clockwise("cw"),
    CounterClockwise("ccw"),
    Flip("flip"),
}

public data class OrientationState(
    val mode: String,
    val rotation: Int,
    val turn: Turn,
)

public object Orientation {
    public fun degrees(surfaceRotation: Int): Int = Math.floorMod(surfaceRotation, 4) * 90

    public fun mode(widthPx: Int, heightPx: Int): String = if (widthPx > heightPx) "landscape" else "portrait"

    public fun turn(previous: Int?, current: Int): Turn {
        if (previous == null) return Turn.None
        return when (Math.floorMod(current - previous, 360)) {
            90 -> Turn.CounterClockwise
            270 -> Turn.Clockwise
            180 -> Turn.Flip
            else -> Turn.None
        }
    }

    public fun next(previous: OrientationState?, surfaceRotation: Int, widthPx: Int, heightPx: Int): OrientationState {
        val rotation = degrees(surfaceRotation)
        val moved = previous != null && previous.rotation != rotation
        val turn = if (moved) turn(previous?.rotation, rotation) else previous?.turn ?: Turn.None
        return OrientationState(mode(widthPx, heightPx), rotation, turn)
    }
}
