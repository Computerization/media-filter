package com.computerization.mediafilter.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Divider
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.computerization.mediafilter.SharedViewModel
import com.computerization.mediafilter.data.AnalyzeResponse
import com.computerization.mediafilter.data.ChatMessage
import com.computerization.mediafilter.data.ChatRequest
import com.computerization.mediafilter.theme.AppColors
import com.computerization.mediafilter.ui.components.ChatBubbleData
import com.computerization.mediafilter.ui.components.ChatBubbleView
import com.computerization.mediafilter.ui.components.InfoCard
import com.computerization.mediafilter.ui.components.VerdictCard
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ResultScreen(
    result: AnalyzeResponse,
    viewModel: SharedViewModel,
    onBack: () -> Unit
) {
    val isDark = isSystemInDarkTheme()
    val chatMessages = remember { mutableStateListOf<ChatBubbleData>() }
    var chatInput by remember { mutableStateOf("") }
    var isChatLoading by remember { mutableStateOf(false) }
    val listState = rememberLazyListState()
    val scope = rememberCoroutineScope()
    val focusManager = LocalFocusManager.current

    val verdictText = when (result.verdict) {
        "reliable" -> "信息可信"
        "misleading" -> "不可信/谣言"
        else -> "需要谨慎"
    }

    val verdictColor = when (result.verdict) {
        "reliable" -> AppColors.accentGreen
        "misleading" -> AppColors.dangerRed
        else -> AppColors.warningOrange
    }

    val inputBg = if (isDark) Color(0xFF1F1F1F) else Color.White
    val cardBg = if (isDark) Color(0xFF262626) else Color.White

    fun sendChatMessage() {
        val text = chatInput.trim()
        if (text.isEmpty()) return
        focusManager.clearFocus()

        // Add user message
        chatMessages.add(ChatBubbleData(role = "user", content = text))
        chatInput = ""

        // Add empty assistant message for streaming
        val assistantId = java.util.UUID.randomUUID().toString()
        chatMessages.add(ChatBubbleData(id = assistantId, role = "assistant", content = "", reasoning = ""))
        isChatLoading = true

        // Build request
        val kmpMessages = chatMessages.dropLast(1).map { ChatMessage(role = it.role, content = it.content) }
        val request = ChatRequest(
            messages = kmpMessages,
            title = result.title,
            originalText = result.originalText,
            analysisSummary = result.summary,
            analysisDetails = result.details
        )

        viewModel.chatStream(
            request = request,
            onChunk = { event, chunk ->
                val index = chatMessages.indexOfFirst { it.id == assistantId }
                if (index >= 0) {
                    val msg = chatMessages[index]
                    if (event == "reasoning") {
                        chatMessages[index] = msg.copy(reasoning = (msg.reasoning ?: "") + chunk)
                    } else if (event == "content") {
                        chatMessages[index] = msg.copy(content = msg.content + chunk)
                    }
                }
                scope.launch {
                    listState.animateScrollToItem(chatMessages.size - 1)
                }
            },
            onComplete = {
                isChatLoading = false
            },
            onError = { error ->
                isChatLoading = false
                val index = chatMessages.indexOfFirst { it.id == assistantId }
                if (index >= 0) {
                    val msg = chatMessages[index]
                    chatMessages[index] = msg.copy(content = "抱歉，出错了：$error")
                }
            }
        )

        scope.launch {
            listState.animateScrollToItem(chatMessages.size - 1)
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("详细报告", fontWeight = FontWeight.SemiBold) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(
                            Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "返回",
                            tint = Color.White
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = AppColors.primaryBlue,
                    titleContentColor = Color.White
                )
            )
        },
        bottomBar = {
            // Chat input bar
            Column {
                Divider()
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(cardBg)
                        .padding(horizontal = 16.dp, vertical = 12.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    TextField(
                        value = chatInput,
                        onValueChange = { chatInput = it },
                        placeholder = { Text("问问助手...", color = Color.Gray) },
                        modifier = Modifier
                            .weight(1f)
                            .border(1.dp, Color.Gray.copy(alpha = 0.2f), RoundedCornerShape(20.dp)),
                        colors = TextFieldDefaults.colors(
                            focusedContainerColor = inputBg,
                            unfocusedContainerColor = inputBg,
                            focusedIndicatorColor = Color.Transparent,
                            unfocusedIndicatorColor = Color.Transparent
                        ),
                        shape = RoundedCornerShape(20.dp),
                        singleLine = true
                    )
                    Spacer(modifier = Modifier.width(12.dp))
                    IconButton(
                        onClick = { sendChatMessage() },
                        enabled = chatInput.isNotEmpty() && !isChatLoading,
                        modifier = Modifier
                            .size(44.dp)
                            .clip(CircleShape)
                            .background(
                                if (chatInput.isEmpty()) Color.Gray
                                else AppColors.primaryBlue
                            )
                    ) {
                        Icon(
                            Icons.AutoMirrored.Filled.Send,
                            contentDescription = "发送",
                            tint = Color.White,
                            modifier = Modifier.size(20.dp)
                        )
                    }
                }
            }
        }
    ) { padding ->
        val bgColor = if (isDark) Color(0xFF1A1A1A) else Color(0xFFF7F7F7)

        LazyColumn(
            state = listState,
            modifier = Modifier
                .fillMaxSize()
                .background(bgColor)
                .padding(padding)
                .padding(horizontal = 20.dp),
            verticalArrangement = Arrangement.spacedBy(20.dp)
        ) {
            item { Spacer(modifier = Modifier.height(4.dp)) }

            // Verdict card
            item {
                VerdictCard(
                    verdictEmoji = result.verdictEmoji,
                    verdictText = verdictText,
                    verdictColor = verdictColor
                )
            }

            // Summary card
            item {
                InfoCard(icon = "📝", title = "简要说明", content = result.summary)
            }

            // Details card
            item {
                InfoCard(icon = "🔍", title = "详细分析", content = result.details)
            }

            // Title card
            item {
                InfoCard(icon = "📰", title = "原文标题", content = result.title)
            }

            // Chat section divider
            item {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 10.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Divider(modifier = Modifier.weight(1f), color = Color.Gray.copy(alpha = 0.2f))
                    Text(
                        "向助手提问",
                        modifier = Modifier.padding(horizontal = 8.dp),
                        fontSize = 12.sp,
                        color = Color.Gray
                    )
                    Divider(modifier = Modifier.weight(1f), color = Color.Gray.copy(alpha = 0.2f))
                }
            }

            // Welcome message
            item {
                ChatBubbleView(
                    ChatBubbleData(
                        role = "assistant",
                        content = "您好！我是您的助手。关于这篇文章，我已经为您做好了分析。如果有任何不明白的地方，请随时问我！"
                    )
                )
            }

            // Chat messages
            items(chatMessages, key = { it.id }) { msg ->
                ChatBubbleView(msg)
            }

            // Loading indicator
            if (isChatLoading) {
                item {
                    Row(modifier = Modifier.padding(start = 10.dp)) {
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(18.dp))
                                .background(cardBg)
                                .padding(14.dp)
                        ) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(20.dp),
                                strokeWidth = 2.dp
                            )
                        }
                    }
                }
            }

            item { Spacer(modifier = Modifier.height(8.dp)) }
        }
    }
}
