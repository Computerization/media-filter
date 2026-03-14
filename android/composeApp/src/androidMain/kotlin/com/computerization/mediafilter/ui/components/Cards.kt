package com.computerization.mediafilter.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.computerization.mediafilter.theme.AppColors

@Composable
fun InstructionCard() {
    val isDark = isSystemInDarkTheme()
    val cardBg = if (isDark) Color(0xFF262626) else Color.White

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .shadow(10.dp, RoundedCornerShape(16.dp))
            .clip(RoundedCornerShape(16.dp))
            .background(cardBg)
            .border(1.dp, AppColors.primaryBlue.copy(alpha = 0.3f), RoundedCornerShape(16.dp))
            .padding(16.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("ℹ️", fontSize = 20.sp)
            Spacer(modifier = Modifier.width(8.dp))
            Text("使用说明", fontWeight = FontWeight.SemiBold, fontSize = 16.sp)
        }

        Spacer(modifier = Modifier.height(12.dp))

        InstructionRow("1", "在微信中打开可疑文章")
        InstructionRow("2", "点击右上角 ··· → 分享")
        InstructionRow("3", "选择「慧眼」即可自动分析")
    }
}

@Composable
private fun InstructionRow(number: String, text: String) {
    Row(
        modifier = Modifier.padding(vertical = 4.dp),
        verticalAlignment = Alignment.Top
    ) {
        Box(
            modifier = Modifier
                .size(22.dp)
                .clip(CircleShape)
                .background(AppColors.primaryBlue),
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = number,
                color = Color.White,
                fontSize = 11.sp,
                fontWeight = FontWeight.Bold
            )
        }
        Spacer(modifier = Modifier.width(12.dp))
        Text(text = text, fontSize = 14.sp)
    }
}

@Composable
fun VerdictCard(
    verdictEmoji: String,
    verdictText: String,
    verdictColor: Color
) {
    val isDark = isSystemInDarkTheme()
    val cardBg = if (isDark) Color(0xFF262626) else Color.White

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .shadow(10.dp, RoundedCornerShape(20.dp))
            .clip(RoundedCornerShape(20.dp))
            .background(
                Brush.linearGradient(
                    colors = listOf(
                        verdictColor.copy(alpha = 0.15f),
                        verdictColor.copy(alpha = 0.05f)
                    )
                )
            )
            .background(cardBg.copy(alpha = 0.5f))
            .border(2.dp, verdictColor.copy(alpha = 0.3f), RoundedCornerShape(20.dp))
            .padding(20.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(text = verdictEmoji, fontSize = 56.sp)
        Spacer(modifier = Modifier.width(16.dp))
        Column {
            Text(
                text = "判定结果",
                fontSize = 12.sp,
                color = Color.Gray
            )
            Text(
                text = verdictText,
                fontSize = 24.sp,
                fontWeight = FontWeight.Bold,
                color = verdictColor
            )
        }
    }
}

@Composable
fun InfoCard(
    icon: String,
    title: String,
    content: String
) {
    val isDark = isSystemInDarkTheme()
    val cardBg = if (isDark) Color(0xFF262626) else Color.White

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .shadow(10.dp, RoundedCornerShape(16.dp))
            .clip(RoundedCornerShape(16.dp))
            .background(cardBg)
            .padding(16.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(icon, fontSize = 16.sp)
            Spacer(modifier = Modifier.width(8.dp))
            Text(title, fontWeight = FontWeight.SemiBold, fontSize = 16.sp)
        }
        Spacer(modifier = Modifier.height(12.dp))
        Text(
            text = content,
            fontSize = 14.sp,
            lineHeight = 22.sp
        )
    }
}

@Composable
fun ConnectionHint() {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(10.dp))
            .background(Color(0xFFFF9900).copy(alpha = 0.1f))
            .padding(horizontal = 16.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text("⚠️", fontSize = 12.sp)
        Spacer(modifier = Modifier.width(8.dp))
        Text(
            text = "如遇连接问题，请更新至最新版本",
            fontSize = 12.sp,
            color = Color.Gray
        )
    }
}

@Composable
fun FooterView() {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 16.dp, bottom = 8.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.Center
        ) {
            Text("🏢", fontSize = 10.sp)
            Spacer(modifier = Modifier.width(4.dp))
            Text(
                text = "Computerization",
                fontSize = 12.sp,
                fontWeight = FontWeight.Medium,
                color = Color.Gray
            )
        }
        Text(
            text = "帮助长辈识别网络虚假信息",
            fontSize = 10.sp,
            color = Color.Gray.copy(alpha = 0.8f)
        )
    }
}
