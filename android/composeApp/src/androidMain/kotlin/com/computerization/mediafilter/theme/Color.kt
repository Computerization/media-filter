package com.computerization.mediafilter.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

object AppColors {
    val primaryBlue = Color(0xFF4A8FD9)
    val accentGreen = Color(0xFF33C759)
    val warningOrange = Color(0xFFFF9900)
    val dangerRed = Color(0xFFE64033)

    @Composable
    fun cardBackground(): Color {
        return if (isSystemInDarkTheme()) Color(0xFF262626) else Color.White
    }

    @Composable
    fun secondaryBackground(): Color {
        return if (isSystemInDarkTheme()) Color(0xFF1A1A1A) else Color(0xFFF7F7F7)
    }

    @Composable
    fun inputBackground(): Color {
        return if (isSystemInDarkTheme()) Color(0xFF1F1F1F) else Color.White
    }
}
