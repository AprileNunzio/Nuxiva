package com.nuxiva.edge.ui

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

class NuxivaTokens(
    val accent: Color,
    val accentSoft: Color,
    val violet: Color,
    val glow: Color,
    val ok: Color,
    val warn: Color,
    val muted: Color,
) {
    val ink: Brush get() = Brush.horizontalGradient(listOf(accent, violet))
    val hairline: Brush get() = Brush.horizontalGradient(listOf(accent.copy(alpha = 0.7f), violet.copy(alpha = 0.35f), Color.Transparent))
}

val LocalTokens = staticCompositionLocalOf {
    NuxivaTokens(Color(0xFF22D3EE), Color(0x2422D3EE), Color(0xFFA78BFA), Color(0x6622D3EE), Color(0xFF34D399), Color(0xFFFBBF24), Color(0xFF8EA0B8))
}

private val DarkTokens = NuxivaTokens(
    accent = Color(0xFF22D3EE),
    accentSoft = Color(0x2422D3EE),
    violet = Color(0xFFA78BFA),
    glow = Color(0x6622D3EE),
    ok = Color(0xFF34D399),
    warn = Color(0xFFFBBF24),
    muted = Color(0xFF8EA0B8),
)

private val LightTokens = NuxivaTokens(
    accent = Color(0xFF0E7490),
    accentSoft = Color(0x1A0E7490),
    violet = Color(0xFF6D28D9),
    glow = Color(0x330E7490),
    ok = Color(0xFF047857),
    warn = Color(0xFFB45309),
    muted = Color(0xFF52627A),
)

private val DarkScheme = darkColorScheme(
    primary = Color(0xFF22D3EE),
    onPrimary = Color(0xFF031B22),
    secondary = Color(0xFF8EA0B8),
    tertiary = Color(0xFFA78BFA),
    background = Color(0xFF05070D),
    onBackground = Color(0xFFE6EDF7),
    surface = Color(0xFF05070D),
    onSurface = Color(0xFFE6EDF7),
    error = Color(0xFFFB7185),
)

private val LightScheme = lightColorScheme(
    primary = Color(0xFF0E7490),
    onPrimary = Color.White,
    secondary = Color(0xFF52627A),
    tertiary = Color(0xFF6D28D9),
    background = Color(0xFFF4F7FB),
    onBackground = Color(0xFF0B1220),
    surface = Color(0xFFF4F7FB),
    onSurface = Color(0xFF0B1220),
    error = Color(0xFFBE123C),
)

private val Display = FontFamily.SansSerif
private val Mono = FontFamily.Monospace

private val NuxivaTypography = Typography(
    displaySmall = TextStyle(fontFamily = Display, fontWeight = FontWeight.Light, fontSize = 40.sp, lineHeight = 46.sp, letterSpacing = (-0.5).sp),
    headlineSmall = TextStyle(fontFamily = Display, fontWeight = FontWeight.Light, fontSize = 26.sp, lineHeight = 32.sp),
    titleLarge = TextStyle(fontFamily = Display, fontWeight = FontWeight.Light, fontSize = 22.sp, lineHeight = 28.sp),
    titleMedium = TextStyle(fontFamily = Mono, fontWeight = FontWeight.Medium, fontSize = 13.sp, lineHeight = 18.sp, letterSpacing = 1.6.sp),
    titleSmall = TextStyle(fontFamily = Display, fontWeight = FontWeight.Medium, fontSize = 15.sp, lineHeight = 20.sp),
    bodyLarge = TextStyle(fontFamily = Display, fontWeight = FontWeight.Normal, fontSize = 16.sp, lineHeight = 24.sp),
    bodyMedium = TextStyle(fontFamily = Display, fontWeight = FontWeight.Normal, fontSize = 14.sp, lineHeight = 21.sp),
    bodySmall = TextStyle(fontFamily = Display, fontWeight = FontWeight.Normal, fontSize = 12.sp, lineHeight = 17.sp),
    labelLarge = TextStyle(fontFamily = Mono, fontWeight = FontWeight.Medium, fontSize = 13.sp, letterSpacing = 1.2.sp),
    labelMedium = TextStyle(fontFamily = Mono, fontWeight = FontWeight.Medium, fontSize = 11.sp, letterSpacing = 1.4.sp),
    labelSmall = TextStyle(fontFamily = Mono, fontWeight = FontWeight.Medium, fontSize = 10.sp, letterSpacing = 1.2.sp),
)

@Composable
fun NuxivaTheme(content: @Composable () -> Unit) {
    val dark = isSystemInDarkTheme()
    CompositionLocalProvider(LocalTokens provides if (dark) DarkTokens else LightTokens) {
        MaterialTheme(
            colorScheme = if (dark) DarkScheme else LightScheme,
            typography = NuxivaTypography,
            content = content,
        )
    }
}
