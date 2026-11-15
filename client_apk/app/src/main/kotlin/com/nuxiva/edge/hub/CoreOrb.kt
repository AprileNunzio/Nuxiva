package com.nuxiva.edge.hub

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.nuxiva.edge.ui.LocalTokens
import com.nuxiva.edge.ui.pulse

@Composable
fun CoreOrb(tone: Color, level: Float, size: Dp, title: String, detail: String, modifier: Modifier = Modifier) {
    val tokens = LocalTokens.current
    val breathe by pulse(0.92f, 1f, 2800)
    Box(modifier.size(size), contentAlignment = Alignment.Center) {
        Canvas(Modifier.size(size)) {
            val radius = size.toPx() / 2f
            val swell = 1f + level.coerceIn(0f, 1f) * SWELL
            drawCircle(
                brush = Brush.radialGradient(listOf(tone.copy(alpha = 0.34f), Color.Transparent), center = center, radius = radius),
                radius = radius * breathe * swell.coerceAtMost(1.18f),
            )
            drawCircle(tone.copy(alpha = 0.5f), radius = radius * 0.66f * (1f + level * 0.08f), style = Stroke(1.5.dp.toPx()))
            drawCircle(brush = tokens.ink, radius = radius * 0.5f * (1f + level * 0.12f), style = Stroke(3.dp.toPx()))
        }
        Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(title, style = MaterialTheme.typography.titleLarge, textAlign = TextAlign.Center, modifier = Modifier.widthIn(max = size * 0.55f))
            Text(detail.uppercase(), style = MaterialTheme.typography.labelSmall, color = tokens.muted, textAlign = TextAlign.Center, modifier = Modifier.widthIn(max = size * 0.55f))
        }
    }
}

private const val SWELL = 0.35f
