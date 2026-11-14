package com.nuxiva.edge.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.grid.GridItemSpan
import androidx.compose.foundation.lazy.grid.LazyGridScope
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

@Composable
fun InfoCard(title: String, modifier: Modifier = Modifier, content: @Composable ColumnScope.() -> Unit) {
    Column(modifier.fillMaxWidth().padding(vertical = 6.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text(title.uppercase(), style = MaterialTheme.typography.titleMedium, color = LocalTokens.current.accent)
        Hairline()
        content()
    }
}

@Composable
fun Hairline(modifier: Modifier = Modifier) {
    Box(modifier.fillMaxWidth().height(1.dp).background(LocalTokens.current.hairline))
}

@Composable
fun KeyValue(label: String, value: String) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.Top) {
        Text(label.uppercase(), style = MaterialTheme.typography.labelMedium, color = LocalTokens.current.muted, modifier = Modifier.weight(0.4f))
        Text(value.ifEmpty { "-" }, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.weight(0.6f))
    }
}

@Composable
fun StatusDot(color: Color, active: Boolean = true, size: Int = 10) {
    val level by pulse(0.45f, 1f, 1400)
    Box(
        Modifier
            .size(size.dp)
            .alpha(if (active) level else 1f)
            .drawBehind {
                drawCircle(color.copy(alpha = 0.35f), radius = this.size.minDimension)
                drawCircle(color, radius = this.size.minDimension / 2f)
            }
            .clip(CircleShape),
    )
}

@Composable
fun Meter(fraction: Float, modifier: Modifier = Modifier, marker: Float? = null) {
    val tokens = LocalTokens.current
    val shown = fraction.coerceIn(0f, 1f)
    Box(
        modifier
            .fillMaxWidth()
            .height(6.dp)
            .clip(RoundedCornerShape(3.dp))
            .background(tokens.accentSoft)
            .drawBehind {
                drawRoundRect(brush = tokens.ink, size = androidx.compose.ui.geometry.Size(size.width * shown, size.height), cornerRadius = androidx.compose.ui.geometry.CornerRadius(3.dp.toPx()))
                if (marker != null) {
                    val x = size.width * marker.coerceIn(0f, 1f)
                    drawLine(tokens.warn, Offset(x, 0f), Offset(x, size.height), strokeWidth = 2.dp.toPx())
                }
            },
    )
}

@Composable
fun Stat(label: String, value: String, modifier: Modifier = Modifier, fraction: Float? = null, marker: Float? = null) {
    Column(modifier.fillMaxWidth().padding(vertical = 6.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text(label.uppercase(), style = MaterialTheme.typography.labelSmall, color = LocalTokens.current.muted)
        Text(value, style = MaterialTheme.typography.headlineSmall)
        if (fraction != null) Meter(fraction, marker = marker)
    }
}

@Composable
fun PrimaryAction(text: String, onClick: () -> Unit, enabled: Boolean = true, danger: Boolean = false) {
    val tint = if (danger) MaterialTheme.colorScheme.error else LocalTokens.current.accent
    Button(
        onClick = onClick,
        enabled = enabled,
        shape = RoundedCornerShape(14.dp),
        colors = ButtonDefaults.buttonColors(containerColor = tint.copy(alpha = 0.16f), contentColor = tint),
        elevation = ButtonDefaults.buttonElevation(0.dp, 0.dp, 0.dp, 0.dp, 0.dp),
    ) { Text(text.uppercase(), style = MaterialTheme.typography.labelLarge) }
}

@Composable
fun ToggleRow(label: String, checked: Boolean, onChange: (Boolean) -> Unit) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Text(label, modifier = Modifier.weight(1f), style = MaterialTheme.typography.bodyMedium)
        Switch(checked = checked, onCheckedChange = onChange)
    }
}

fun LazyGridScope.fullSpan(key: Any? = null, content: @Composable () -> Unit) {
    item(key = key, span = { GridItemSpan(maxLineSpan) }) { content() }
}
