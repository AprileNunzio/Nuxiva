package com.nuxiva.edge.ui

import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext

private val LightScheme = lightColorScheme(
    primary = Color(0xFF0E7490),
    onPrimary = Color.White,
    secondary = Color(0xFF475569),
    background = Color(0xFFF8FAFC),
    surface = Color(0xFFFFFFFF),
    error = Color(0xFFB91C1C),
)

private val DarkScheme = darkColorScheme(
    primary = Color(0xFF22D3EE),
    onPrimary = Color(0xFF031B22),
    secondary = Color(0xFF94A3B8),
    background = Color(0xFF030712),
    surface = Color(0xFF0F172A),
    error = Color(0xFFF87171),
)

@Composable
fun NuxivaTheme(content: @Composable () -> Unit) {
    val dark = isSystemInDarkTheme()
    val context = LocalContext.current
    val scheme = when {
        Build.VERSION.SDK_INT >= Build.VERSION_CODES.S && dark -> dynamicDarkColorScheme(context)
        Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> dynamicLightColorScheme(context)
        dark -> DarkScheme
        else -> LightScheme
    }
    MaterialTheme(colorScheme = scheme, content = content)
}
