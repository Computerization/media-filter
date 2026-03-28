package com.computerization.mediafilter.ui

import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.computerization.mediafilter.SharedViewModel
import com.computerization.mediafilter.data.AnalyzeResponse
import com.computerization.mediafilter.theme.AppColors
import com.computerization.mediafilter.ui.components.AnimatedGradientBackground
import com.computerization.mediafilter.ui.components.ConnectionHint
import com.computerization.mediafilter.ui.components.FooterView
import com.computerization.mediafilter.ui.components.InstructionCard
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(
    viewModel: SharedViewModel,
    initialSharedText: String?,
    sharedTextFlow: SharedFlow<String>,
    onNavigateToResult: (AnalyzeResponse) -> Unit
) {
    val isDark = isSystemInDarkTheme()
    var inputText by remember { mutableStateOf(initialSharedText ?: "") }
    var isLoading by remember { mutableStateOf(false) }
    val snackbarHostState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()
    val clipboardManager = LocalClipboardManager.current
    val focusManager = LocalFocusManager.current

    val buttonScale by animateFloatAsState(
        targetValue = if (isLoading) 0.98f else 1f,
        animationSpec = spring(stiffness = Spring.StiffnessMedium),
        label = "buttonScale"
    )

    // Auto-analyze if text was shared
    var hasAutoAnalyzed by remember { mutableStateOf(false) }
    LaunchedEffect(initialSharedText) {
        if (!initialSharedText.isNullOrEmpty() && !hasAutoAnalyzed) {
            hasAutoAnalyzed = true
            isLoading = true
            viewModel.analyzeContent(inputText) { response, error ->
                isLoading = false
                if (error != null) {
                    scope.launch { snackbarHostState.showSnackbar(error) }
                } else if (response != null) {
                    onNavigateToResult(response)
                }
            }
        }
    }

    // Listen for new shared text
    LaunchedEffect(Unit) {
        sharedTextFlow.collect { text ->
            inputText = text
            isLoading = true
            viewModel.analyzeContent(text) { response, error ->
                isLoading = false
                if (error != null) {
                    scope.launch { snackbarHostState.showSnackbar(error) }
                } else if (response != null) {
                    onNavigateToResult(response)
                }
            }
        }
    }

    fun analyze() {
        if (inputText.isBlank()) return
        focusManager.clearFocus()
        isLoading = true
        viewModel.analyzeContent(inputText) { response, error ->
            isLoading = false
            if (error != null) {
                scope.launch { snackbarHostState.showSnackbar(error) }
            } else if (response != null) {
                onNavigateToResult(response)
            }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("慧眼", fontWeight = FontWeight.SemiBold) },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = AppColors.primaryBlue,
                    titleContentColor = Color.White
                )
            )
        },
        snackbarHost = { SnackbarHost(snackbarHostState) }
    ) { padding ->
        AnimatedGradientBackground(modifier = Modifier.padding(padding)) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .verticalScroll(rememberScrollState())
                    .imePadding()
                    .padding(horizontal = 20.dp, vertical = 16.dp),
                verticalArrangement = Arrangement.spacedBy(24.dp)
            ) {
                // Instruction card
                InstructionCard()

                // Input card
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
                        Text("📄", fontSize = 16.sp)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("文章链接或文字内容", fontWeight = FontWeight.SemiBold, fontSize = 16.sp)
                    }
                    Spacer(modifier = Modifier.height(12.dp))

                    val inputBg = if (isDark) Color(0xFF1F1F1F) else Color.White
                    TextField(
                        value = inputText,
                        onValueChange = { inputText = it },
                        placeholder = {
                            Text(
                                "请粘贴微信文章链接或输入需要鉴别的文字...",
                                color = Color.Gray.copy(alpha = 0.6f)
                            )
                        },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(140.dp)
                            .border(
                                1.dp,
                                Color.Gray.copy(alpha = 0.2f),
                                RoundedCornerShape(12.dp)
                            ),
                        colors = TextFieldDefaults.colors(
                            focusedContainerColor = inputBg,
                            unfocusedContainerColor = inputBg,
                            focusedIndicatorColor = Color.Transparent,
                            unfocusedIndicatorColor = Color.Transparent,
                        ),
                        shape = RoundedCornerShape(12.dp)
                    )
                }

                // Action buttons
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Button(
                        onClick = {
                            clipboardManager.getText()?.text?.let { inputText = it }
                        },
                        modifier = Modifier.weight(1f),
                        colors = ButtonDefaults.buttonColors(containerColor = AppColors.primaryBlue),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Text("📋 粘贴", modifier = Modifier.padding(vertical = 6.dp))
                    }

                    Button(
                        onClick = { inputText = "" },
                        modifier = Modifier.weight(1f),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = if (isDark) Color(0xFF404040) else Color(0xFFE6E6E6)
                        ),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Text(
                            "🗑️ 清空",
                            color = if (isDark) Color.White else Color.Black,
                            modifier = Modifier.padding(vertical = 6.dp)
                        )
                    }
                }

                // Analyze button
                Button(
                    onClick = { analyze() },
                    modifier = Modifier
                        .fillMaxWidth()
                        .scale(buttonScale),
                    enabled = !isLoading && inputText.isNotBlank(),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = Color.Transparent,
                        disabledContainerColor = Color.Transparent
                    ),
                    shape = RoundedCornerShape(16.dp)
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(
                                Brush.horizontalGradient(
                                    if (isLoading) listOf(Color.Gray, Color.Gray)
                                    else listOf(AppColors.accentGreen, AppColors.accentGreen.copy(alpha = 0.8f))
                                ),
                                RoundedCornerShape(16.dp)
                            )
                            .padding(vertical = 14.dp),
                        horizontalArrangement = Arrangement.Center,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        if (isLoading) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(20.dp),
                                color = Color.White,
                                strokeWidth = 2.dp
                            )
                            Spacer(modifier = Modifier.width(10.dp))
                            Text("正在分析...", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 18.sp)
                        } else {
                            Text("🔍", fontSize = 18.sp)
                            Spacer(modifier = Modifier.width(10.dp))
                            Text("开始分析", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 18.sp)
                        }
                    }
                }

                // Connection hint
                ConnectionHint()

                // Footer
                FooterView()
            }
        }
    }
}
