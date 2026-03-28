package com.computerization.mediafilter.ui.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.computerization.mediafilter.theme.AppColors

data class ChatBubbleData(
    val id: String = java.util.UUID.randomUUID().toString(),
    val role: String,
    var content: String,
    var reasoning: String? = null
)

@Composable
fun ChatBubbleView(msg: ChatBubbleData) {
    val isUser = msg.role == "user"
    var isReasoningExpanded by remember { mutableStateOf(true) }
    val isDark = isSystemInDarkTheme()

    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start
    ) {
        if (isUser) Spacer(modifier = Modifier.width(50.dp))

        Column(
            horizontalAlignment = if (isUser) Alignment.End else Alignment.Start
        ) {
            // Reasoning section
            val reasoning = msg.reasoning
            if (!reasoning.isNullOrEmpty()) {
                Column(modifier = Modifier.padding(bottom = 4.dp)) {
                    Row(
                        modifier = Modifier
                            .clip(RoundedCornerShape(12.dp))
                            .background(AppColors.primaryBlue.copy(alpha = 0.1f))
                            .clickable { isReasoningExpanded = !isReasoningExpanded }
                            .padding(horizontal = 10.dp, vertical = 6.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("✨", fontSize = 10.sp)
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = if (isReasoningExpanded) "收起思考过程" else "查看深度思考",
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Medium,
                            color = AppColors.primaryBlue
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = if (isReasoningExpanded) "▲" else "▼",
                            fontSize = 8.sp,
                            color = AppColors.primaryBlue
                        )
                    }

                    AnimatedVisibility(
                        visible = isReasoningExpanded,
                        enter = expandVertically() + fadeIn()
                    ) {
                        Text(
                            text = reasoning,
                            fontSize = 12.sp,
                            color = Color.Gray,
                            modifier = Modifier
                                .padding(top = 4.dp)
                                .clip(RoundedCornerShape(8.dp))
                                .background(Color.Gray.copy(alpha = 0.05f))
                                .padding(10.dp)
                                .heightIn(max = 150.dp)
                                .verticalScroll(rememberScrollState())
                        )
                    }
                }
            }

            // Main content
            if (msg.content.isNotEmpty()) {
                Text(
                    text = msg.content,
                    color = if (isUser) Color.White else if (isDark) Color.White else Color.Black,
                    modifier = Modifier
                        .shadow(3.dp, RoundedCornerShape(18.dp))
                        .clip(RoundedCornerShape(18.dp))
                        .background(
                            if (isUser) AppColors.primaryBlue
                            else if (isDark) Color(0xFF262626) else Color.White
                        )
                        .padding(14.dp)
                )
            }
        }

        if (!isUser) Spacer(modifier = Modifier.width(50.dp))
    }
}
